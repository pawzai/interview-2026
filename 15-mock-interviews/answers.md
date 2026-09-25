# Answers

Grading keys for [questions.md](questions.md). Numbers match the question numbers exactly.

These are **not** lessons in Java, AWS or retrieval - packs `01` to `11` own that depth and are referenced rather than restated. Each entry here gives what a strong answer must contain, the **follow-up ladder** the interviewer will climb next, the **red flags** that cost you the round, and where to go for the mechanism.

Q72-Q77 are run as complete design rounds in [scenario-questions.md](scenario-questions.md), Part B. Q186-Q191 have no scripted answer on purpose - they are your stories, and Part C of the scenarios says how to build them.

Everything here assumes the frameworks defined once in [../01-java/README.md](../01-java/README.md): the **four-layer** technical answer (direct answer, mechanism, trade-off, experience hook), **CIDER** for scenarios, **STAR-L** for behavioral questions.

---

## 1. How a principal-level loop is run and scored

### Q1. What the loop is actually deciding

The loop is not deciding whether you can do the job. It is deciding **whether a group of people who have each spent 45 minutes with you will collectively defend hiring you at a level, in a room, using written evidence**.

Three consequences follow, and they should change how you prepare:

- **The unit of output is a written note, not a conversation.** Whatever the interviewer cannot write down did not happen. An answer that was brilliant but unquotable scores lower than a clear answer with one number in it.
- **The decision is about risk, not ceiling.** At principal level the question is "what is the chance this person is a problem in eighteen months", so evidence of judgement, self-correction and disagreement handling outweighs one more correct mechanism.
- **Level is decided separately from hire.** You can be a clear hire at one level below the one you applied for, which is the most common bad outcome for a 19-year candidate who answers everything at senior depth.

**Say it in the room like this:** give them a sentence they can copy verbatim into the notes. "We cut p99 from 1.4 seconds to 240 milliseconds by moving the fan-out off the request path" is a note. "We improved performance significantly" is not.

### Q2. Round types and the signal each one owns

| Round | The one signal it owns | What it is not measuring |
| --- | --- | --- |
| Recruiter screen | Basic fit, level plausibility, compensation range | Technical depth |
| Hiring manager | Scope match, motivation, how you would operate on their team | Algorithms |
| Coding / pairing | Can you still produce working code and collaborate while doing it | Cleverness (Q148) |
| Deep technical dive | Depth on demand - three levels of "why" (Q30) | Breadth |
| System design | Structured ambiguity handling and trade-off reasoning (Q60) | Getting the "right" design |
| Architecture / code review | Judgement about other people's work, and how you deliver criticism (Q163) | Whether you would have built it that way |
| Behavioral / leadership | Influence, conflict, ownership, evidence of learning (Q176) | Technical detail |
| Bar raiser | Consistency across the loop, and the level call (Q192) | Any single topic |

**The useful move:** at the start of each round, ask *"what would you like to get out of the next 45 minutes?"* It costs twenty seconds and tells you which signal to optimize for.

### Q3. What actually happens in a debrief

Interviewers write independent feedback (usually before seeing each other's), then the panel meets. The chair walks round by round, asks for the **evidence** behind each score, and looks for two things: **a consistent story** and **a disqualifying data point**.

- Scores are not averaged. A specific, well-evidenced concern from one interviewer outweighs three "seemed good" positives, because the positive notes are not falsifiable and the concern is.
- Disagreement is resolved by asking *"what did you see?"* This is why generic answers are dangerous: they leave your advocates with nothing to say on your behalf.
- The level call happens here, and is usually made on the design and behavioral rounds rather than the coding round.

**Preparation consequence:** you are writing your advocate's script during the loop. Give at least one quotable, specific, numeric artifact per round.

### Q4. Two strong hires and one evidenced no hire `[T]`

The no hire usually wins, or the loop is extended with another round - which is a materially worse position than a clean pass.

The asymmetry exists because a specific negative is **falsifiable evidence** and a general positive is not. "He could not explain why his own retry design would not duplicate the payment" is a sentence a panel can act on. "Strong communicator" is not.

**What that implies for your preparation:** your marginal hour is worth more spent removing a weakness than deepening a strength. Specifically, spend it on the topic you would least like to be asked about, because the interviewer who finds it is the one whose note decides the loop. This is also the argument for mock interviews with a peer who will actually push (Q14) rather than reading answers you already agree with.

### Q5. Leveling, and what moves the needle

Leveling is decided on **scope of impact** and **ambiguity tolerated**, not years or depth.

| Evidence in the notes | Reads as |
| --- | --- |
| "Solved a hard problem well" | Senior |
| "Chose not to solve it, and redefined the problem so it did not need solving" | Principal |
| "Knows the mechanism deeply" | Senior |
| "Knows the mechanism and the cost of using it at our size" | Principal |
| "Led a project" | Senior |
| "Changed how three teams work, and it stuck after he left" | Principal |
| "Handled the incident" | Senior |
| "Changed the class of incident so it stopped recurring" | Principal |

**The pattern:** principal-level evidence is about **second-order effects** - what happened to the organization, the cost curve, or the failure class, not what happened to the ticket. Every story in your bank should have that second sentence attached.

### Q6. What a usable piece of evidence looks like

An interviewer's note is usable if a stranger reading it can tell what you did and how hard it was. The shape is: **context with a number, decision with an alternative rejected, outcome with a number, and something you learned.**

> Weak: "Has experience with performance tuning."
> Usable: "Diagnosed a p99 regression to connection-pool exhaustion under retry storms; chose to bound retries with a budget rather than enlarge the pool because the pool was masking the real fault; p99 1.4s to 240ms, and he added the retry-budget metric to the platform template so other teams inherited it."

**How you hand them one:** end substantial answers with a compressed version of that sentence. Not a story - a caption. The four-layer answer's fourth layer is exactly this, and most candidates drop it under time pressure.

### Q7. The four things always being scored

Regardless of the nominal topic:

1. **Depth on demand.** Can you go three levels deeper than your first answer (Q30)?
2. **Trade-off literacy.** Does every answer carry a cost, an alternative and a condition under which you would decide differently?
3. **Production judgement.** Have you operated this, or only built it? Incidents, rollbacks, cost, migrations, on-call.
4. **Communication and collaboration.** Can the interviewer follow you, and is working with you pleasant?

The fourth is the one senior candidates discount and bar raisers weight heavily. A round can be lost purely on the interviewer having to work hard to follow you.

### Q8. Correct answers, no hire `[T]`

- **Level mismatch.** Every answer was correct at senior depth. No second-order impact, no organizational scope, no "and then I changed how we do this" (Q5).
- **No trade-offs.** Answers were assertions. The panel could not tell whether you understand *when not to* do the thing you recommended, which at principal level is the whole job.
- **Unpleasant to work with.** You corrected the interviewer three times, or you dismissed their system, or you never once said "that is a good point, I had not considered it". This is the most common invisible failure, because nobody tells you.

Two more that show up in debriefs: **no curiosity** (you asked nothing about their problems) and **the same story three times** (Q182).

### Q9. Budgeting 45 minutes

A workable default for a technical round: 3 minutes of framing and scoping, 30-32 minutes of substance, 5 minutes for the interviewer's remaining must-ask questions, 5 minutes for your questions.

**The most common misallocation is front-loading.** Candidates spend 15 minutes on the first sub-topic because they know it well, and the interviewer never gets to ask the two questions that would have distinguished them. The fix is mechanical: **say the shape first** ("there are four parts to this - I will do each in about two minutes and go deeper wherever you want"), then keep to it, then explicitly offer depth. That single sentence also demonstrates the structuring the round is scoring.

In a design round the split is different and is covered in Q60 and Q71.

### Q10. What a mock is for, and what makes one worthless

A mock exists to produce **failure under realistic conditions, cheaply**. Its output is a list of things that broke - not a feeling that it went well.

A mock is worthless when:

- **You are both the interviewer and the interviewee, silently.** Reading a question and thinking "I know that" is not practice; the failure mode being trained is *speaking* under time pressure, and it is not exercised.
- **There is no clock.** Time pressure is the variable that causes almost every real failure (Q203).
- **There are no follow-ups.** The whole game at this level is the second and third "why" (Q30). A mock without a ladder trains the wrong skill.
- **You stop when it goes badly.** The recovery is the most valuable thing to rehearse (Q193).

**Minimum viable mock:** a timer, a question you have not scripted, speaking out loud, a recording, and one page of notes afterwards.

### Q11. Self-scoring without a partner

Record audio. Then score against a fixed rubric rather than a memory of how it felt, because the memory is systematically generous.

Record for each answer: **time taken**, whether you gave a **number**, whether you named a **trade-off**, whether you had an **experience hook**, and where you **hesitated or padded**. Padding is audible on a recording and invisible in the moment - phrases like "so basically" and "as I mentioned" cluster exactly where you are not sure.

Two metrics worth tracking session over session: **time to first structured sentence** (should be under 15 seconds) and **percentage of answers with at least one number**. Both are objective and both correlate with how the round is scored (Q6).

### Q12. Your mock score improved three times `[T]`

The likely artifact is **memorization of the specific answer**, not improvement in answering. You are measuring recall of a script under conditions that will not recur - the real interviewer will phrase it differently and follow up somewhere else.

Controls:

- **Rotate the question set.** A question you have answered should not reappear for at least two weeks.
- **Score the process, not the content.** Did you scope before answering? Did you offer a trade-off unprompted? Those transfer; the content does not.
- **Have the partner change the follow-up path,** so the second and third level are never the same.
- **Introduce an adjacent question you have not prepared** in every session, and score only that one.

The general principle is the one from evaluation discipline in `../08-genai/answers.md`: a test set you have iterated against is no longer a test set.

### Q13. A six-week mock schedule `[A]`

Three sessions a week, eighteen sessions. Constraint: full-time job, so each session is 60-75 minutes including the debrief.

| Week | Session 1 | Session 2 | Session 3 |
| --- | --- | --- | --- |
| 1 | Screen and positioning (Cat 2) | Java and Spring deep dive (Cat 3) | Design round, framing only - first 15 minutes, three times |
| 2 | Microservices deep dive (Cat 4) | Full design round Q72 | Behavioral: three stories, timed (Cat 13) |
| 3 | AWS round (Cat 6) | Database round (Cat 7) | Full design round Q76 |
| 4 | DevOps and incident command (Cat 8) | Coding round, 45 minutes (Cat 11) | AI round (Cat 9) |
| 5 | Security round (Cat 10) | Architecture review (Cat 12) | Full design round Q75 |
| 6 | Full loop day: [mocks/loop-01](mocks/loop-01-java-platform-principal.md) or the matching archetype | Bar raiser and curveballs (Cat 14) | Reverse interview and negotiation (Cat 15), plus a re-run of your weakest round |

**Rules that make the schedule work:** the design rounds are always full length and always recorded; every session ends with one page of notes; the weakest round from weeks 1-4 gets re-run in week 6 with a different question. Reading time is not scheduled here - it belongs to the packs themselves, and if the material is not known, the mock is premature.

### Q14. Calibrating with a peer outside your domain `[A]`

The problem: a peer who does not know AWS cannot tell whether your answer was right, so their score is noise unless you change what they score.

**Give them the observable rubric.** They can reliably score four things without domain knowledge: did the candidate scope before answering; was the structure statable in one sentence afterwards; were trade-offs explicit; was there a number. Have them score only those, 1-4, with one line of evidence each.

**Give them the follow-up ladder in writing.** Take it from this pack - each answer here has one. They do not need to understand the answer to ask "why?" and then "what would make you change that?" and then "what breaks first at ten times the volume?"

**Give them a stop rule.** "If you cannot restate my answer in one sentence, mark it unclear and tell me." That single instruction produces the most valuable feedback a non-expert can give, and it maps directly to the fourth thing every interviewer scores (Q7).

**Calibrate the calibrator once:** run one session where you deliberately give a bad answer and one where you give a strong one, and check that their scores separate. If they do not, the rubric is too abstract - make it more behavioral.

---

## 2. Recruiter and hiring-manager screen

### Q15. The 90-second introduction

Structure: **now, arc, proof, aim** - roughly 20, 25, 30 and 15 seconds.

> "I am a principal-level engineer at Sonata Software, currently leading Java and Spring Boot services on AWS with a security and AI focus. My arc is nineteen years across three companies: I started in .NET at Nittany, spent twelve years at Verizon India where I moved from .NET into Java and Spring as we broke telecom-scale systems into services, and since 2022 at Sonata I have been doing Java 17 and Spring Boot on AWS, with AI engineering from 2024. The work I would point at is *[one system, with a scale number]* and *[one AI feature, with a cost or quality number]*. What I am looking for now is a role where the architecture decisions and the standards across teams are mine to own, which is why this conversation interested me."

**Why it is shaped that way:** it ends on *their* problem rather than your history, which invites the next question you want. It also plants the level claim ("standards across teams") early, which is what Q5 says the loop decides.

**Red flags:** chronological narration from 2007 forward, no numbers, ending on "and that is my background" with nothing for them to grab.

### Q16. "Walk me through your resume"

Do not walk it. **Frame it, then walk the last two roles and offer the rest.** Nineteen years narrated linearly will consume the screen and bore the listener.

> "There is a twelve-year Verizon chapter and a Sonata chapter, and the through-line is that I have built the same architectural patterns in two ecosystems. Shall I spend most of the time on the last five years and come back to Verizon if it is relevant?"

**What they listen for at each transition:** why you left (never blame), what changed in your scope, and whether the story is consistent with the resume dates. Unexplained transitions are the thing they are checking.

Attach one artifact per chapter: at Verizon the scale, at Sonata the AWS and AI work. Two numbers total is enough for a screen.

**Follow-up ladder:** "Why did you move from .NET to Java?" (Q20) → "What was your actual role in that migration?" → "Who disagreed with you?"

### Q17. "Why are you looking?" without criticizing the employer `[T]`

The rule: **pull, not push.** Say what you are moving *toward*. Every complaint about Sonata, however justified, is heard as a preview of how you will describe them in two years.

> "Nothing is wrong at Sonata - I would recommend the team. The honest answer is that the architecture decisions I most want to be making are decided a level above the role I am in, and the AI platform work I have been driving since 2024 is not the core of the business. I want a role where that is the mandate rather than something I create room for."

**What makes it credible:** it is specific, it is about scope rather than money or people, and it contains a small, non-damaging admission. A completely frictionless answer sounds rehearsed.

**Red flags:** "the management is toxic", "no growth" with no detail, or a long pause before answering.

### Q18. "Why this role?" when the recruiter found you

Do not fake enthusiasm about a company you researched for six minutes. **Be honest about the sequence and specific about the hypothesis.**

> "A recruiter approached me, so I will be straight: I did not come looking. What made me take the call was *[one specific thing - the domain, the scale, the fact that they run Java on AWS at a size where the problems are real]*. What I do not yet know is whether the role has the scope it sounds like, and that is mostly what I want to work out today."

That last clause is doing real work: it turns the screen into a two-way conversation and sets up your questions (Q209) as legitimate rather than presumptuous.

**Red flag:** reciting the company's mission statement back to them. Everyone can tell.

### Q19. Nineteen years, no manager title `[T]`

Frame it as a **fork you took deliberately**, with evidence that you did the leadership part anyway.

> "I went down the technical track on purpose. I have had the choice twice and both times chose the architecture side, because the work I am good at is the design and the standards rather than the headcount. What I did not skip is the leadership: *[the standard you drove across teams you did not own, the engineers you mentored to independence, the incident you commanded]*."

**The trap** is defensiveness - explaining at length why management is not for you. One sentence on the choice, then straight to evidence. The interviewer is not questioning your worth; they are checking whether "principal" means anything in your case (Q5).

**Follow-up ladder:** "How do you get things done without authority?" (Q180) → "Tell me about someone who did not agree" → "What happened after you left?"

### Q20. The .NET-to-Java transition as an asset

The asset framing is **comparative**: you have implemented the same architectural patterns in two independent ecosystems, so you can tell which parts are essential and which are framework accidents.

Make it concrete rather than philosophical. Dependency injection, declarative transactions, an ORM's identity map, an async model - you have seen two implementations of each, and the differences tell you what the pattern actually is. That is a genuinely rare vantage point and it is the reason you are hard to fool by a framework's marketing.

**When the same story sounds like a gap:** if you date your Java from 2016 and then answer Java questions at 2016 depth. The asset framing only survives if the depth is current - virtual threads, records, sealed types, the current GC choices (`../01-java`). Prepare one modern-Java answer specifically to close this.

### Q21. "What is your current compensation?"

Never volunteer the current number. Redirect to **expectation**, and anchor the expectation on the role.

> "I would rather talk about the range for the role than my current number, because they are set by different things. Based on the scope we have described, I am looking at *[range]*. If that is inside your band, everything else is a detail."

If pressed hard and the question is legal where you are, giving a total-compensation figure including variable pay is better than stonewalling into hostility - but always paired with the expectation, so the current number does not become the anchor.

Where the question is banned, say so calmly and give the expectation. See Q214 for the case where you have no signal about their range at all.

### Q22. "What would you do in your first 90 days?"

The structure that works when you do not know the systems: **learn, prove, change** - 30 days each, with the explicit statement that the plan is a hypothesis you expect to revise.

- **Days 1-30, learn:** read the incident history and the on-call rotation before the code; get on-call shadow if possible; map the top five services, their owners and their SLOs; find out where the money goes. Ship something small on day one so the deployment path is in your hands.
- **Days 31-60, prove:** take one real, visible problem with a measurable outcome - a p99, a cost line, a flaky pipeline - and fix it end to end. Credibility at principal level is bought with a delivered thing, not with a document.
- **Days 61-90, change:** propose one structural change with the evidence gathered in the first sixty days, and get it agreed rather than announced.

**The sentence that makes this land:** "I would want to be careful about proposing an architecture in the first month - I have seen people do that and spend a year paying for it."

### Q23. "Are you hands-on?" `[T]`

Proof is specific and recent. Claims are worthless here because everyone says yes.

**Proves it:** "I wrote the retry-budget filter that is in our platform starter"; "I was on the pager last month and here is what I did at 2am"; a debugging story with the actual tool named and the actual finding; an opinion about a language feature that only someone who has fought it would hold.

**Fails:** "I stay hands-on through code reviews" (that is oversight, not hands-on), "I do proofs of concept" with no example, or naming a technology you last wrote in 2019.

**The honest calibration** is better than an overclaim: "I write code most weeks, but I am not the fastest person on the team at it any more - what I am is the person who can read the whole system. If the role needs the top-throughput coder, I am not that." At principal level that answer scores; a bluff that collapses in the coding round does not.

### Q24. What the recruiter's technical questions are testing

Not depth. They are testing **whether the resume is yours**, and calibrating the level so they route you to the right loop.

A recruiter with a crib sheet asks "what is dependency injection" or "what is the difference between SQS and Kinesis". The scoring is binary: fluent and unbothered, or hesitant. So answer **short and plainly**, without jargon, and stop. Over-answering a screening question is a small negative signal - it reads as not knowing what the question was for.

**One thing worth doing:** ask what the technical loop consists of. Recruiters answer this honestly and it is the single most useful piece of information you can get in the screen.

### Q25. Establishing the real scope before you commit

Four questions, all askable in a screen without arrogance:

- "Is this a new role or a backfill? If a backfill, what did that person do?"
- "Who makes the architecture decisions today, and what would change if I joined?"
- "How many teams would this role touch, and do I have any formal authority over them?"
- "What is the first problem you would want this person on?"

The last one is the highest-yield question in the entire screen. The answer is either a **class of problem** ("our services do not have a coherent story for data consistency") which indicates real scope, or a **task** ("we need someone to finish the migration") which indicates a senior role with a principal title (Q26).

### Q26. Principal title, senior contractor job description `[T]`

Probe by **asking about the decisions, not the title.** Titles are cheap; decision rights are not.

> "What would this person be expected to decide on their own, and what would they take to someone else? And can you give me an example from the last quarter where someone at this level changed the direction of something?"

If they cannot produce an example, the role is execution-shaped. That is legitimate information, not a reason to be rude - and it is better learned now than in week three.

**How to keep it inoffensive:** attribute the ambiguity to the industry rather than to them. "Principal means five different things across companies I have talked to, so I have started asking about decisions instead."

**Do not** conclude the role is beneath you and disengage. Sometimes the JD is old, or written by HR, and the manager is describing something much bigger.

### Q27. "Moving from a monolith to microservices" - five questions `[A]`

That sentence tells you almost nothing, and the answers change how you run the entire loop.

- **"What is the business outcome you are buying with this?"** Deployment independence, team autonomy, scaling one hot path, or a compliance boundary? If the answer is "it is the modern architecture", you have learned that your job would be partly to slow this down (Q59), and you should test that appetite now.
- **"How far in are you, and what has gone wrong so far?"** "We are 18 months in with four services and a shared database" is a completely different role from "we start next quarter".
- **"Is the database split, and if not, what is the plan?"** This one question separates teams who understand the problem from teams who have moved code around. See `../03-microservices` Categories 4-5.
- **"Who owns the services after the split - are the teams reorganizing too?"** Conway's law question. If the org is not changing, the services will not stay independent.
- **"What is your deployment frequency and change failure rate today?"** If they cannot deploy the monolith safely, microservices will multiply that problem, and saying so carefully is a strong signal (`../07-devops`).

**What you do with the answers:** they tell you which pack the loop will actually test, and whether the design round is likely to be a decomposition exercise (Q58).

### Q28. Positioning the same history three ways `[A]`

Same facts, different **spine**. Do not invent anything; change what the arc is *about*.

| Role | The spine | Lead artifact | What you downplay |
| --- | --- | --- | --- |
| **Platform principal** | Nineteen years of building the same patterns twice, now spent on making other teams faster | The standard, starter or library other teams adopted; the incident class you eliminated | Individual feature delivery |
| **Solution architect** | Telecom scale into cloud economics - designs that survive contact with cost and compliance | An end-to-end architecture with the scale numbers and the cost model; the migration you owned | Deep language internals |
| **AI engineering lead** | An engineer who brought production discipline to AI, rather than a researcher | The AI feature with cost, evaluation and guardrails, and the thing you refused to build (`../10-ai-agents` Q3) | Long pre-2016 history |

**The rules:** the 90-second intro (Q15) changes; the resume does not. Your weakest framing is the one where the last five years are not the centre of the story. And in every version, the .NET chapter is compressed to one clause - it buys the comparative point (Q20) and nothing else.

---

## 3. Java and Spring deep-dive round

### Q29. "Tell me about HashMap"

A shallow prompt is an **invitation to choose your own depth**. The move is to answer the literal question in two sentences, then explicitly offer the level below - and let them pick.

> "It is an array of buckets with a hash-and-mask index, chaining on collision, and since Java 8 a bucket converts to a red-black tree past eight entries with the table at least 64, so a degenerate hash degrades to log n rather than n. The parts that actually bite in production are the resize behaviour and what happens when a key's `hashCode` and `equals` are inconsistent or mutable. Where would you like me to go - the concurrency story, the memory footprint, or a bug I have actually had with it?"

**Why this scores:** it demonstrates depth without a lecture, it hands them the steering wheel (which reads as collaborative), and the phrase "a bug I have actually had" invites the production-judgement thread you want (Q7).

**Red flags:** reciting the default capacity and load factor as the substance of the answer, or talking for four minutes without pausing.

**Depth:** `../01-java` Categories 1-2.

### Q30. Three levels of "why" on `@Transactional`

Have the ladder rehearsed as three distinct plateaus, because the interviewer is testing whether your knowledge bottoms out.

1. **What:** it is declarative transaction demarcation - Spring starts a transaction before the method and commits or rolls back after, based on the propagation and rollback rules.
2. **How:** it is an AOP proxy. Spring wraps the bean; the proxy opens the transaction and binds the connection to the thread through `TransactionSynchronizationManager`. **Therefore self-invocation bypasses it entirely**, and `private` methods are never advised.
3. **Why that design, and what it costs:** proxying keeps the transaction concern out of the code, but it makes the boundary invisible at the call site, which is why the self-invocation bug is so common and so hard to see in review. The alternatives are weaving at compile time (surprising in a different way) or programmatic `TransactionTemplate` (explicit, verbose, and what I use when the boundary is subtle).
4. **The fourth level, if they keep going:** rollback only on unchecked exceptions by default; `readOnly` is a hint whose effect depends on the JPA provider and driver; the transaction ends at commit but the connection may not be returned when you think it is; and combining it with `@Async` or a reactive stack moves the whole thread-binding assumption out from under you.

**The tell that you are ready:** each level should be sayable without needing the previous one as a run-up.

**Depth:** `../02-spring` transactions category.

### Q31. Asked about something you have not used in production `[T]`

**What scores:** name the boundary, then demonstrate that you understand the mechanism and what you would check before adopting it.

> "I have not run that in production, so I will separate what I know from what I would verify. The mechanism is *[X]*. What I would want to know before using it is *[the two things that would actually decide it]*, and I would find that out by *[a specific test]*."

That answer is often scored *higher* than a thin claim of experience, because it demonstrates calibration - which is exactly what a principal is trusted for.

**What fails:** bluffing. The interviewer asks about it precisely because they have used it, and the follow-up will be about a sharp edge you cannot know about. The recovery from a caught bluff costs more than the honest answer ever would (Q195).

**The one thing not to do:** apologize repeatedly. State the boundary once, then be useful.

### Q32. "How would you find a memory leak in a running service?"

The first sentence must be **evidence before hypothesis**. Interviewers are listening for whether you jump to a cause.

> "First I would establish that it is a leak rather than a workload change or a cache doing its job - is heap after full GC trending up over days, and did anything deploy? Then I would take a heap histogram, and only if that is inconclusive a full heap dump on a canary instance, because a dump on a production node with a large heap can pause it long enough to matter."

Then the ladder: dominator tree, not the biggest object list. Classloader leaks look different from object leaks. Off-heap and native memory are a separate hunt (direct buffers, `Metaspace`, a native library) and the JVM's heap metrics will not show them. Thread-local retention behind a pooled executor is the classic Java-web version.

**The production-judgement markers** the interviewer is waiting for: doing this on a canary, the cost of the dump, having the artifact retained for later, and knowing that the fix might be a bound rather than a cure.

**Depth:** `../01-java` JVM category.

### Q33. What concurrency questions are actually about

Not `synchronized`. At this level they are about **the memory model and the failure modes you cannot test for**: visibility versus atomicity, happens-before, why a race passes a thousand test runs and fails in production, and what you do structurally so the question stops arising.

Steer there deliberately. When asked "what does `volatile` do", answer it in one sentence and then move up: "the more useful version of that question is how I decide between `volatile`, an `Atomic`, a lock and just not sharing the state - and my default is the last one, because the cheapest concurrency bug is the one that is structurally impossible."

Then have ready: thread-pool sizing tied to whether the work is CPU- or IO-bound, what virtual threads change about that calculation (Q35), and one real story - a deadlock, a lost update, or a `ConcurrentModificationException` that only happened under load.

**Depth:** `../01-java` concurrency category.

### Q34. The interviewer says something wrong about the memory model `[T]`

The goal is to be right **without making them wrong in public**. Frame it as a question or as your own uncertainty, and let the mechanism do the work.

> "That might be a difference in how we are using the term - my understanding is that `volatile` gives visibility and ordering but not compound atomicity, so a `volatile` counter increment can still lose updates. Is there a case you have seen where it holds?"

Three properties of that response: it is not a contradiction, it states the mechanism precisely enough that a knowledgeable interviewer immediately sees who is right, and it gives them a graceful exit.

If they insist and it is material, **let it go** and move on: "Fair enough, I would want to check that." Winning the point is worth nothing; the note that says "corrected me three times" is worth a lot, negatively. If it is a deliberate test - and it often is - the calm, precise, non-combative version is exactly what they wanted to see (Q194).

### Q35. "Virtual threads - would you use them?"

Avoid both failure modes by answering with **the shape of the workload**, not an opinion about the feature.

> "For a service that is mostly blocking IO with a thread-per-request model, yes - that is precisely what they are for, and the win is that you stop sizing a pool against downstream latency. For CPU-bound work they change nothing; the parallelism is still your core count. And there are two things I would check before switching: pinning on `synchronized` blocks holding a monitor across a blocking call, and any code that relies on thread-locals or on the pool as an implicit concurrency limit - because removing that limit can turn a well-behaved service into a load generator against a downstream that has not changed."

That last clause is the principal-level part: **removing a bottleneck relocates it**. Finish with what you would need in place first - a bulkhead or semaphore where the pool used to be the limiter.

**Depth:** `../01-java` concurrency and Java 21 material.

### Q36. Three Spring mechanisms to draw from memory

- **The bean lifecycle**, including where `BeanPostProcessor` sits and therefore where proxies get created - because that is the answer to half the "why doesn't my annotation work" questions.
- **The security filter chain**, in order, with `SecurityContextHolder` and where authentication is actually established (Q38).
- **The MVC request path**: `DispatcherServlet` to handler mapping to handler adapter to argument resolvers to the return-value handler and message converters - because exception handling, content negotiation and validation all hang off specific points on it.

**What failing to draw them signals:** that you use Spring as a set of annotations. At principal level, the expectation is that you can debug it when it misbehaves, and the debugging is always about which of these three ran, in what order, and what it wrapped.

**Depth:** `../02-spring` Categories 1-4.

### Q37. "Why Spring Boot rather than plain Spring?"

**The answer everyone gives:** auto-configuration, embedded server, starters, less XML. True, unremarkable, and scored as a memorized list.

**The answer that scores:** Boot's real product is **opinionated defaults with a documented escape hatch**, and the value is organizational rather than technical.

> "The technical content is auto-configuration and starters. But the reason I would choose it is that it makes the boring decisions identically across forty teams, so a service is legible to someone who has never seen it - the same actuator endpoints, the same config precedence, the same metrics. That is a platform property, not a framework feature. The cost is that when a default is wrong for you, you are debugging a conditional configuration you did not write, so I want the team to know how to read `--debug` auto-configuration output before they need it."

Then the trade-off you would name unprompted: Boot's defaults assume a fairly standard web service, and the further you are from that - unusual startup ordering, a non-standard transaction manager, native images - the more the defaults cost you.

### Q38. You blank on the filter order `[T]`

Do not stall or guess a list. **Convert it from recall to reasoning**, out loud.

> "I do not want to recite an order I might get wrong, so let me derive it. Whatever restores the context has to come before anything that reads it, so context persistence is early. Anything that establishes authentication comes before authorization, so the authentication filters sit in the middle. The authorization filter is effectively last because it needs the fully populated context. Exception translation has to wrap the authentication filters to turn their exceptions into a challenge, so it sits outside them. That gives me: context, then exception translation, then authentication, then authorization - and CSRF early because it should reject before anything expensive."

**Why this scores better than the memorized list:** it demonstrates that you understand *why* the order is what it is, which is the thing that transfers when you have to insert a custom filter. Naming that you are deriving rather than recalling is honest and costs nothing.

**Depth:** `../02-spring` Spring Security category; `../11-security` Categories 2-4.

### Q39. Reading 30 lines with a subtle bug

Reading order, said out loud as you go:

1. **What is it supposed to do?** State the intent in one sentence before criticizing anything. If you cannot, ask.
2. **The signature and the lifecycle.** Is this a Spring bean? A singleton? Is any of this state shared across threads? Most subtle bugs in a 30-line Java class are here.
3. **Mutable state, then the boundaries** - fields, collections handed in or returned, anything `static`.
4. **Error and edge paths** - what happens on an exception halfway through, on empty, on null, on a duplicate.
5. **Only then style.**

Narrating this order is worth as much as finding the bug: it shows a repeatable method rather than a lucky spot. If you find the bug in the first ten seconds, still say the method - "I think I see it, but let me read properly so I do not miss a second one" - because the round is scoring your review process (Q167).

### Q40. "How would you test that?" after every answer

It is probing three things at once: whether you actually build the things you describe, whether you know what is hard to test about them, and whether you distinguish **what you would test** from **what you would monitor**.

The strongest form of the answer names the boundary: "I would unit test the decision logic with a fake clock, contract test the boundary so the other team's change breaks my build, and for the concurrency behaviour I would not write a test at all - I would make the state unshared, because a test that passes a thousand times proves nothing there."

**Why the third repetition is easier:** by then you should be pre-empting it. Append the testing sentence to your answers before being asked, and the interviewer marks it as a habit rather than a response. That is a cheap, visible upgrade in a deep-dive round.

**Depth:** `../02-spring` testing category; `../07-devops` Category 2.

### Q41. N+1 as a production story

The definition takes ten seconds and scores nothing. Make it an incident.

> "N+1 is one query for the parents and then one per child collection because the association is lazy and something touched it in a loop. The version worth talking about is how it got to production: it does not show up in tests with three rows, and it does not show up in the code, because the trigger is a getter in a serializer. We found it as a p99 that scaled with page size. The fix was a fetch join for that path plus an entity graph, but the durable fix was the one that stopped it recurring - we added a per-request query counter that fails the build in the integration tests above a threshold, and logs a warning in production."

**The structure is deliberate:** mechanism, why it escapes review, how it was detected, the fix, then **the change that removed the class of bug**. That last clause is the principal-level marker from Q5, and it converts a textbook topic into leveling evidence.

**Depth:** `../02-spring` Spring Data category; `../06-database` Category 4.

### Q42. Opinion questions with an unknown audience `[T]`

Answer with the **decision rule**, not the verdict. Then state your default and the condition that would change it. You cannot be wrong about a rule, and it invites them to share their context.

> "Lombok - my rule is that I will take a code generator for the mechanical parts as long as the team can read the generated result and the build does not depend on IDE plugins being installed correctly. In practice I use `@Getter`, `@Builder` and `@RequiredArgsConstructor`, avoid `@Data` on JPA entities because of `equals` and `hashCode` on a mutable id, and for new code prefer records where they fit. What is the convention here?"

**The failure modes are symmetrical:** a dogmatic answer alienates half of all interviewers, and a completely non-committal answer reads as having no engineering opinions. Take a position - just make it a conditional one.

**Do not** try to read their preference off their face and match it. Interviewers notice, and it is the worst possible signal in a round that is partly about whether you will disagree with them later.

### Q43. Designing a library API for forty teams `[A]`

The round is not scoring API aesthetics. It is scoring whether you understand that **a shared library is a distributed system with a human release cycle**.

What the strong answer covers, roughly in this order: who the users are and what their failure looks like when you are wrong; the smallest possible public surface, with everything else genuinely inaccessible; **versioning and deprecation policy stated before the first method**, because you will never get all forty teams onto a new major version simultaneously; what happens when a team needs something you did not anticipate (an extension point, or your phone number); defaults that are safe rather than fast; observability built in, so a team using it badly is visible to you; and the migration path from whatever they do today.

**The trade-off to name unprompted:** a library couples forty teams to your release cadence, and a service couples them to your uptime. Say which you would choose here and why - that single sentence is the difference between a senior and a principal answer.

**Depth:** `../01-java` Category 3; `../03-microservices` Category 2.

### Q44. Defending Java and Spring against Go `[A]`

Do not defend the language. **Reframe as a decision with inputs**, then take a real position.

> "The honest answer is that both are fine and the choice is rarely about the language. The inputs I would use are: what the team already operates well, what the workload looks like, and what the ecosystem gives me for free. For a service that is mostly IO with heavy transactional data access, the Spring ecosystem gives me transaction management, security, data access and observability that I would otherwise assemble by hand, and Java's operational tooling - JFR, heap dumps, async-profiler - is genuinely better when something goes wrong at 2am. Where I would pick Go: a small network-heavy component with a tight memory budget, a CLI, a sidecar, anything where a 40 MB static binary and a fast cold start matter more than the ecosystem."

Then concede honestly - startup time and memory footprint used to be a real Java disadvantage in serverless and sidecar contexts, and CRaC and native images are a real but not free answer - and close on the organizational point: "the strongest argument for either is that this team can debug it under pressure."

**Red flag:** treating it as an attack. It is almost always a test of whether you hold technology opinions loosely.

---

## 4. Distributed systems and microservices round

### Q45. "How do you decide a service boundary?" in 60 seconds

> "I start from the business capability and the data it owns, not from the code. A boundary is right when the service owns its data outright, when a typical change lands in one service, and when the team can deploy it without coordinating. The test I actually apply is the change-coupling one: if two services always ship together, that is one service with a network call in the middle. The counter-pressure is that every boundary you draw converts a method call into a partial failure, so the burden of proof is on splitting."

**Why this earns the follow-up you want:** it plants three hooks - data ownership, change coupling, partial failure - and the interviewer will pull one. All three lead somewhere you have depth.

**Red flags:** starting with "one service per team" or "per aggregate" as a rule with no reasoning, or not mentioning data ownership at all.

**Depth:** `../03-microservices` Category 1.

### Q46. Exactly-once, without pedantry

The correct content is that exactly-once **delivery** is not achievable over an unreliable network, but exactly-once **processing** is - at-least-once delivery plus idempotent or deduplicated handling, or a transactional read-process-write inside one system.

The pedantry risk is in the delivery. Lead with the practical answer and let the theory be one clause:

> "In practice you get exactly-once processing by combining at-least-once delivery with a deduplication key or an idempotent operation - delivery itself cannot be exactly-once, which is why the effort goes into the consumer. Concretely: a business idempotency key, stored in the same transaction as the effect, so a redelivery is a no-op rather than a second charge."

Then offer the harder half unprompted, because it is where the real signal is: **the effect and the dedup record must commit atomically**, which is why the outbox pattern exists (Q48) and why "we check Redis first" is a race, not a solution.

**Depth:** `../03-microservices` Categories 3-4.

### Q47. "We use two-phase commit across our services" `[T]`

Assume they have a reason. Ask before disagreeing - and if they do have a legitimate one (an XA-capable resource pair, a low-throughput internal flow), you have avoided an embarrassing lecture.

> "Interesting - is that XA across the databases, or a coordinator you built? … The reason I ask is that the failure mode I worry about is the coordinator dying between prepare and commit, which leaves the participants holding locks with no one to tell them what to do. At low volume that is survivable because a human can resolve it. Where it has hurt teams I have worked with is availability coupling: with 2PC, every participant has to be up for any write to succeed. Has that bitten you, or is the volume low enough that it does not?"

**The structure:** question, then the specific mechanism (blocking coordinator, availability coupling), then hand it back. You have demonstrated the knowledge without saying "that is wrong".

**Only then** offer the alternative - saga with compensations, or collapsing the two services if they need atomicity that badly, which is the answer nobody gives and is often right (Q59).

### Q48. Saga versus outbox in two sentences

> "A saga is about **business atomicity across services** - a sequence of local transactions with a compensating action for each, so a failure halfway is unwound semantically rather than rolled back. The outbox is about **atomicity between a database write and a message publish inside one service** - you write the event to a table in the same transaction as the state change, and a relay publishes it, so you can never have one without the other."

Then why the confusion is common and worth naming: they usually appear together. A saga step is implemented *using* an outbox, because each step must reliably announce that it happened. Saying that out loud - "they are at different levels; the outbox is how a saga step keeps its promise" - is the sentence that shows you have built one.

**Follow-up ladder to expect:** "who relays the outbox?" → "what about ordering and duplicates?" → "how do you handle a compensation that itself fails?" (the answer is that it must be retriable forever and eventually alert a human; there is no third option).

**Depth:** `../03-microservices` Categories 3-4.

### Q49. "Tell me about a distributed failure you debugged"

Use CIDER, but the load-bearing part is the **isolation** - it is where the evidence of real experience is.

The structure that lands: one sentence of system context with a scale number; how you *knew* (the alert or the symptom, with the number); the hypotheses you held and **how you discriminated between them** with data; the finding, including the thing that surprised you; the immediate mitigation separated from the root-cause fix; and what class of failure you eliminated afterwards.

**The details that make it credible:** the tool you actually used, the false lead you followed first, and a timestamp or duration. Stories with no false lead sound reconstructed, because real debugging always has one.

**Keep it to three minutes** and offer depth: "that is the summary - I can go deeper on the detection or on the fix, whichever is more useful."

### Q50. "We use an idempotency key" - three levels down

- **Level 1 - where does the key come from?** Weak: the service generates it. Strong: the *client* supplies it, scoped to the operation, because a retry by the client must carry the same key, and only the client knows that two requests are the same intent.
- **Level 2 - what do you store, and when?** Weak: "we check if we have seen it". Strong: you store the key **and the response**, in the same transaction as the effect, and you return the stored response on replay. Checking-then-acting in two steps is a race under concurrent retries; you need a unique constraint doing the work, or a row lock.
- **Level 3 - the concurrent in-flight case and expiry.** What happens when the retry arrives while the first request is still running? (Reject with a conflict, or block on the lock - but decide, because the default is a double effect.) How long do you keep keys, and what happens to a retry after expiry? What if the request body differs for the same key - is that a client bug you must reject, and do you hash the body to detect it?

**A fourth level if they keep going:** idempotency across a saga is not the same as idempotency of one endpoint, and the retry may arrive at a different instance or after a failover.

**Depth:** `../03-microservices` Category 3.

### Q51. Monolith migration in ten minutes `[T]`

**Signal the omission explicitly** - that is the whole test. Silently giving a shallow answer looks like a shallow understanding; announcing the cut looks like judgement.

> "In ten minutes I will give you the sequencing and the first two decisions, and skip the org design and the data migration mechanics, which are the two hardest parts - flag me if you would rather I spend the time there instead."

Then the content, compressed: do not start with code, start with **why** (Q27); pick the first slice by change frequency and data independence, not by what is easiest; strangler fig with a facade so the callers do not change; **the database is the whole problem** - a service with a shared database is a distributed monolith; keep the monolith authoritative until the new path is verified with dual reads and comparison; and have a rollback that is a routing change rather than a data migration.

**What you kept:** the sequencing and the data point. **What you cut:** everything you named. That framing is worth more than the extra content would have been.

### Q52. What makes a retry answer senior

Mediocre: "retry with exponential backoff and jitter, and use a circuit breaker."

The single addition that makes it senior: **retries are a load amplifier, so they need a budget, not just a policy.**

> "Backoff and jitter are table stakes. The two things I care about more are: retries must only apply to idempotent operations, or you need the key from the previous question; and the total retry load has to be bounded across the fleet, because every layer retrying three times gives you 27x amplification at the bottom during exactly the incident where the downstream is already failing. So a retry budget - a cap on the ratio of retries to requests, shed when exceeded - and retries at one layer only, usually the outermost."

Then the circuit breaker's real purpose, which most answers get wrong: it is not to protect the caller, it is to **stop the caller from preventing the callee's recovery**. And name what you would monitor: retry ratio, and the breaker's state transitions as an event, not a gauge.

**Depth:** `../03-microservices` Category 6.

### Q53. "How do services find each other?"

Answer the surface in one sentence - client-side or server-side discovery, a registry or DNS or the platform's service objects - and then say where the interesting part is, because the question is a doorway:

> "Mechanically it is a registry with health checks, or the platform's DNS. The parts that have actually caused me problems are the two edges: **health check semantics** - liveness versus readiness, and what a service reports when its downstream is down, because a service that fails its own health check because Redis is slow will remove the entire fleet from rotation - and **deregistration lag**, where an instance is gone but callers keep dialing it for the TTL, which is what makes a rolling deploy look like an error spike."

That reframing shows operational experience and gives the interviewer three follow-up paths. Have connection draining and pre-stop hooks ready for the deploy path.

**Depth:** `../03-microservices` Category 7; `../07-devops` Kubernetes category.

### Q54. Proving you have operated a broker

Read versus operated is visible in **which details you volunteer**. Operators talk about the things that are not in the tutorial:

- **Consumer lag** as the primary metric, and what you did when it grew - and the distinction between lag caused by slow consumers and lag caused by a stuck partition.
- **Rebalancing**: what a rebalance does to in-flight processing, why a long poll interval causes one, and the day a deploy caused a storm of them.
- **Partition count** as a decision that is hard to change, and what determines it (ordering requirements and consumer parallelism, not throughput alone).
- **Poison messages**: the dead-letter path, and the fact that you have to be able to *replay* from it, which almost nobody builds until they need it.
- **Retention** and the moment you discovered it was shorter than your recovery time.

One story with three of these in it is worth more than a complete conceptual explanation.

**Depth:** `../03-microservices` Categories 3 and 9.

### Q55. "Do you version your APIs?" `[T]`

Everyone says yes. The follow-up is **"how do you retire a version?"** - and that is where most answers collapse, because versioning is easy and deprecation is organizational.

The answer that survives:

> "Yes, but the versioning scheme matters less than the retirement process, and that is the part that is hard. Concretely: additive-only changes within a version, so consumers do not break; a new version only for a breaking change, which I try very hard to avoid; and for retirement, **usage telemetry per consumer per version** so I know exactly who is still on the old one, a deadline agreed with those teams rather than announced, and a scheduled brownout - a deliberate short outage of the old version before the real cutoff - because that is the only thing that reliably finds the callers who did not read the email."

The brownout detail is the one that marks real experience. Then name the trade-off: every version you keep alive is a branch in your code and your test matrix forever, which is why consumer-driven contract tests are the durable answer.

**Depth:** `../03-microservices` Category 2.

### Q56. Consistency without reciting CAP

CAP is a partition-time statement and almost never the question being asked. Answer in terms of **what the user is promised**.

> "I would rather talk about it per operation than per system. For each one I ask: what does the user see if they read immediately after their own write, and what is the worst staleness that is acceptable? Most systems need read-your-own-writes for the actor and are happy with seconds of staleness for everyone else - and that is a routing decision, not a database choice: send that user's reads to the primary or to a session-pinned replica, and everything else to the replicas."

Then the vocabulary that shows depth: strong versus eventual is too coarse; the useful distinctions are **read-your-writes, monotonic reads, and bounded staleness**, plus the fact that a cache in front of a strongly consistent store makes the system eventually consistent regardless of the store's guarantees.

**Depth:** `../03-microservices` Category 4; `../06-database` Category 8.

### Q57. One anecdote covering tracing, sampling and cardinality

One story is better than three because it demonstrates that these interact, which is the actual insight.

> "We had a latency problem visible only at p99, so tracing was the right tool - except our head-based sampling at one percent meant we almost never captured a slow request. We moved that service to tail-based sampling so we kept the slow and errored traces and dropped the fast ones. The knock-on was cost: tail sampling means buffering, and our first attempt blew the collector's memory. And the related mistake in the same investigation was that someone had added the customer id as a metric label to help debug it, which multiplied our time series by the customer count and nearly took out the metrics backend - the id belongs on the span, not on the metric."

**Why this scores:** three concepts, one narrative, a cost consequence, and a stated rule (high-cardinality identifiers go on traces and logs, never on metric labels).

**Depth:** `../07-devops` Category 8.

### Q58. Decomposing their product live with no domain knowledge `[A]`

You are not being tested on their domain - you are being tested on **how you extract a domain from a stranger in ten minutes**. Run it as an interview of them.

Sequence: ask them to name the top five *nouns* the business cares about, and who changes each one; ask what changes most often and what has never changed; ask where the pain is today - what is slow to deploy, what breaks together, who has to be in the room for a release; sketch capabilities rather than services and check the data ownership for each; then propose a **first slice only**, with the reason it is first and the reason the rest waits.

**The judgement markers:** you asked before you drew; you proposed one slice rather than a target architecture; you named what you would *not* split and why; and you said what evidence would change your mind after the first slice ships.

**Red flag:** producing a full microservice diagram for a business you learned about six minutes ago. It reads as pattern application, not thought.

### Q59. Arguing against a split, to someone who just did one `[A]`

The trap is that this sounds like criticizing their decision. Separate **the general case** from **their case**, and be genuinely curious about theirs.

> "I would want to know what they bought with it first - if it was deployment independence and they got it, that is a win and I would say so. My general position is that the burden of proof is on splitting, because a split converts a compile-time error into a runtime partial failure, adds a network hop to every interaction, and turns a transaction into a saga. So my test is: are these two things deployed together anyway, do they change together, and does the data cross the boundary in every request? If yes to all three, the split has paid all the costs and bought nothing. What did the split give you here?"

Then the constructive alternative you would offer instead of a split - modular monolith with enforced module boundaries, a separate deployment only for the component with a genuinely different scaling profile.

**What is being scored:** whether you can hold a strong architectural position while remaining pleasant to disagree with (Q7, Q166). The content matters less than the tone.

---
## 5. System design round

> Q72-Q77 are run in full in [scenario-questions.md](scenario-questions.md), Part B.

### Q60. The first four minutes

In order: **restate, scope, constrain, plan.**

1. **Restate the problem in one sentence** and get agreement. Thirty seconds, and it has caught a misunderstanding for me more than once.
2. **Functional scope**: name five candidate features and ask them to pick the two or three that matter. You are not guessing what is in scope, you are negotiating it.
3. **Non-functional constraints with numbers**: users, requests per second, read-write ratio, data size and growth, latency target, consistency requirement, availability target. Ask; if they say "you decide", state an assumption out loud and write it down.
4. **Say the plan**: "I will do the API and data model, then the high-level architecture, then go deep on whichever component you find most interesting, then failure modes and cost. Does that order work for you?"

**What must not happen:** drawing a box in the first four minutes. Boxes before requirements is the single most reliable predictor of a bad design round, and interviewers are explicitly watching for it.

### Q61. Extracting requirements from a vague interviewer

Vagueness is usually deliberate, and the test is whether you can **make decisions under it** rather than extract your way out. So: ask a small number of high-leverage questions, then **assume out loud** and move.

The high-leverage ones - the ones whose answers change the architecture - are: read-heavy or write-heavy and by what ratio; how much data and over what horizon; what is the tightest latency requirement and on which operation; and what is the consistency requirement on the one operation that matters. Four questions, ninety seconds.

Everything else you assume: "I will assume 10 million daily actives and a 100:1 read-write ratio; that gives me roughly *[n]* requests per second at peak. Tell me if that is off by an order of magnitude, because it changes the storage choice."

**Too many questions** is a real failure mode - past four or five, it reads as stalling or as needing to be told what to build. The rule: ask what changes the design, assume the rest, and label every assumption so it can be corrected.

### Q62. Estimation out loud

You need a small table in your head, and you need to be comfortable being **wrong by less than an order of magnitude**. Precision beyond one significant figure is a waste of round time and interviewers will say so.

| Quantity | Number to carry |
| --- | --- |
| Seconds in a day | ~100,000 (86,400) |
| 1 million writes/day | ~12 per second average, so plan for 30-60 at peak |
| Peak-to-average | 2-5x for consumer traffic, higher with a daily batch |
| A row with a few columns | ~1 KB, so 1M rows/day ≈ 1 GB/day ≈ 365 GB/year |
| A modern server | tens of thousands of simple requests/second; a single Postgres, low thousands of transactions/second |
| Memory | 100 GB of RAM is a normal cache node; a billion 100-byte items is not going in it |
| Latency | memory ns, SSD ~100 µs, same-region network ~0.5 ms, cross-region 50-150 ms, disk seek ~10 ms |

**How to say it:** "a million writes a day is about twelve a second, call it fifty at peak - that is nothing, so the write path is not the problem; the problem is the *[fan-out / storage growth / read amplification]*." The purpose of estimation is to **eliminate concerns**, and saying which concern you just eliminated is what scores.

**Depth:** `../04-system-design` Category 2.

### Q63. "Assume infinite scale, do not worry about numbers" `[T]`

Do not accept it. Politely convert it into a bounded number, because "infinite" removes the only thing that makes design decisions decidable.

> "I will keep it light, but I need one number or every choice becomes arbitrary - a design for a thousand requests per second and one for a million are different systems, and I would rather show you the reasoning than pick the most expensive option by default. Can I assume *[a specific figure]* and revise if you want to see it at another scale?"

Almost always they say yes, and the exchange itself is a positive signal: it shows you know that scale is the input that determines the answer.

If they genuinely refuse, **design for a stated tier and name the breakpoints**: "this design holds to roughly *[X]*; the first thing that breaks past that is *[Y]*, and the change is *[Z]*." Naming breakpoints is a better answer than any single design.

### Q64. Driving the whiteboard

The failure mode is a candidate drawing in silence while the interviewer watches. Fix it with three habits:

- **Announce before you draw.** "I am going to put the write path across the top and the read path underneath, so we can talk about them separately." Now they are following a structure, not decoding a picture.
- **Draw the data flow, not the org chart.** Number the steps of a request and walk them. A diagram with no arrows labelled is not a design.
- **Checkpoint every five to seven minutes.** "That is the write path - does that hold up for you, or do you want to push on it before I move to reads?" This is the single highest-value habit in a design round: it prevents you spending fifteen minutes on something they did not care about, and it makes the round feel collaborative.

Keep the board legible - a small number of boxes, with the interesting complexity inside one of them rather than spread over twenty. And **leave space**; you will need to add the failure and scale story later.

### Q65. Depth versus breadth, and who decides

**They decide, and you make it easy for them to.** Get to a complete, coherent, shallow end-to-end design first - that is the thing you must have on the board by roughly the halfway mark - then offer the deep dive.

> "That is the system end to end. The three places where I think the real difficulty is are *[the fan-out]*, *[the consistency of the ledger]* and *[the re-indexing path]*. Which would you like me to go into?"

Two reasons this is right. First, a design that is deep in one place and missing an end is scored as incomplete; a shallow-but-complete design is scored as a design. Second, offering the candidates demonstrates that you know where the difficulty is - which is itself a strong signal, independent of which one you then explore.

**When you should override them:** if there is a correctness problem in a component they did not pick, say it before moving on. "I will go into caching as you asked - I want to flag first that the current write path can lose an event, and I would like to come back to it."

### Q66. Thirty minutes in, no numbers `[T]`

What has gone wrong: you have been designing a **shape** rather than a **system**, and none of your component choices are yet justified. The interviewer's notes probably say "did not size anything", which at principal level is a leveling issue (Q5).

Recover without restarting:

> "Let me put numbers on this before I go further, because I have been designing without them. *[Do the arithmetic out loud - requests per second, storage per year, the size of the hot set.]* That tells me *[the read path is the whole problem / this fits on one machine / the cache does not fit in memory]*, and it means I would change *[the specific component]*."

The recovery is stronger than never having had the problem, if the arithmetic **changes a decision**. If your numbers confirm everything you already drew, it looks like a retrofit - so pick the number that actually challenges something, and say what it challenges.

### Q67. Data model without losing fifteen minutes

Show the **entities, their keys, and the one or two access patterns that drive the design** - not the columns.

> "Four entities: user, document, version, and the extraction result. The key decision is the partition key on the version table, because the dominant query is 'latest version for a document' at high volume and 'all versions for an audit' rarely. So I partition by document id and keep a pointer to the latest, rather than sorting on write time."

That is 25 seconds and it contains the actual design content. Columns, types and nullability contain none of it in this setting.

**The rule:** in a design round the data model exists to justify the storage choice and the query path. If a detail does not change either, leave it out - and say "I will skip the field-level detail unless you want it", so the omission is visible as a choice.

### Q68. A new requirement at minute 35

Being tested: whether your design has **seams**, and whether you handle a change without defensiveness. The wrong instinct is to defend the existing design or to rebuild it.

The sequence: **absorb, locate, cost, decide.**

> "Good - so now we also need per-region data residency. Let me find where that lands. It does not affect the API or the write path, it lands entirely on storage placement and on the routing tier. The cheap version is to route at the edge on the user's home region and keep regional stores that never replicate across the boundary; the cost is that cross-region queries become a fan-out and the global search index has to be rebuilt per region or dropped. I would take the cheap version and drop global search for now, and I would tell you that if global search is a hard requirement, the design changes materially - that is a different conversation."

**The markers:** you located the blast radius before proposing anything, you gave a cost, and you named the condition under which the answer changes.

### Q69. Failure modes and SLOs without an ops lecture

Attach them to components rather than delivering them as a section. **One sentence per box, at the moment you draw the box**: "if this cache is cold or gone, we serve from the database at maybe five times the latency, which is degraded but not down - that is deliberate."

Then, at the end, spend ninety seconds on the two or three failures that are **not** graceful, because those are the design content: the single points of failure, the thing that loses data rather than availability, and the failure that is silent.

State one SLO and derive from it, rather than listing many: "if the target is 99.9 percent on the read path, that is about 43 minutes a month, which means a single-AZ database is already out of budget."

**The trap** is enumerating every failure mode in the system. Interviewers stop listening, and the signal - can you tell which failures matter - is lost in the list.

### Q70. "Would you use Kafka here?" `[T]`

The trap is answering the product question. Almost always the interviewer wants to know **whether you know what property you need**, and a component name reveals nothing.

> "It depends what I need from it, so let me say what the requirement is: I need durable, ordered-per-key delivery with replay, and multiple independent consumers reading the same stream at their own pace. If that is the requirement, then yes - Kafka or Kinesis, and I would choose on operational fit rather than features. If what I actually need is a work queue with per-message acknowledgement, competing consumers and a dead-letter path, then SQS is a better fit and Kafka is the wrong shape. Given what we have described, the fan-out to three consumers is what pushes me to the log."

Then the cost, unprompted: a log is an operational commitment - partitions, consumer groups, rebalancing, retention - and if this is the only place you need it, that is a large fixed cost for one feature.

**Depth:** `../03-microservices` Category 9; `../05-aws` Category 7.

### Q71. The last three minutes

Do not trail off, and do not keep adding boxes. Close deliberately:

- **Summarize in three sentences**: what the design is, and the two decisions that define it.
- **Name the weakest part yourself.** "The part I am least happy with is *[X]* - it works but it couples *[A]* to *[B]*, and with more time I would look at *[the alternative]*." Volunteering this is one of the strongest signals available in the round; it demonstrates that you evaluate your own work, and it pre-empts the criticism.
- **State the first thing that breaks at ten times the scale**, and what you would change.
- **Ask one question** about how they solved it, if they have. It converts the last minute into a conversation and often gets you genuinely useful information.

**What to write down before you stop talking:** nothing new. The board should end with the assumptions from minute three still visible, because they are the justification for everything on it.

---

## 6. Cloud and AWS round

### Q78. "Walk me through what happens when a request hits your architecture"

Expected shape: a **narrated path with a decision at each hop**, not a list of services. Roughly eight to ten hops, thirty seconds each, and you should be able to say what happens if each one fails.

> "DNS resolves through Route 53 with a latency policy to the nearest region. TLS terminates at CloudFront, which serves static assets from cache and forwards the rest to a regional ALB via an origin group with failover. WAF sits at the edge with rate rules per IP and per API key. The ALB routes by path to target groups on ECS Fargate; health checks are on a readiness endpoint that does not check downstream dependencies, deliberately. The service authenticates the caller against a JWT verified with a cached JWKS, authorizes against *[the model]*, reads from Aurora with the reader endpoint for queries and the writer for commands, and writes an event to the outbox table in the same transaction. A relay publishes to EventBridge, which fans out to the consumers…"

**What makes it score:** the small justifications embedded in it - "does not check downstream dependencies, deliberately" (Q53), the outbox in the same transaction (Q48), the reader endpoint. Each one is an invitation to a follow-up you are ready for.

**Red flag:** naming services without saying why any of them is there.

### Q79. The compute decision tree, out loud

> "I decide in this order. **How long does one unit of work run?** Over fifteen minutes, Lambda is out. **How spiky is it?** Idle most of the time with sharp bursts favours Lambda or Fargate; steady, predictable load favours EC2 or ECS on EC2 with savings plans, because at high steady utilization serverless is the expensive option. **What is the latency requirement?** If cold start on the p99 matters and the runtime is heavy, that pushes to a warm service. **What does the team operate well?** A team with no Kubernetes experience should not get EKS for three services. **What is the state?** Anything with a long-lived connection - WebSockets, streaming - changes the answer."

Then land it: "for most of the services I have built - steady traffic, a few hundred requests per second, JVM runtime - ECS on Fargate is the default, and I move to EC2 when the bill or a specialized instance type justifies the operational cost."

**Depth:** `../05-aws` Category 6; `../05-aws/core-services` Categories 1 and 11.

### Q80. "Lambda is cheaper" `[T]`

It is true in a range, and the honest answer names the range and the crossover.

> "Cheaper per request at low or spiky volume, and it also removes work you would otherwise pay a person for. It stops being cheaper at sustained high utilization, because you are paying for GB-seconds with no commitment discount, while a reserved or savings-plan EC2 fleet at seventy percent utilization is dramatically cheaper per unit of compute. The crossover depends on the memory setting and duration, so the way I would settle it is arithmetic rather than opinion: *[requests per month × duration × memory]* against the equivalent fleet. And I would include the costs people leave out on both sides - API Gateway or the ALB, NAT data processing, and the engineering time for the parts serverless removes."

**The principal-level addition:** cost is rarely the deciding factor at small scale, and at large scale it deserves a real model rather than a rule of thumb. Offer to do the arithmetic if they want - it is a strong move and it is Q85's answer too.

### Q81. IAM at architect level

A console-driven answer talks about users, groups and attaching managed policies. An architect answer is about **identity as the boundary**:

- **Roles, not users.** Workloads assume roles; humans federate through SSO into roles with a session. Long-lived access keys are an incident waiting to be reported, and their absence is a design property you can assert.
- **The trust policy is the security control**, not the permission policy. Who can assume this role, from where, under what conditions - and for cross-account or third-party access, the external id and the confused deputy problem.
- **Boundaries you cannot exceed**: service control policies at the organization level, permission boundaries for delegated administration, so a team can create roles without escalating.
- **How you actually reach least privilege**: not by writing it by hand, but by starting broad in non-production with Access Analyzer or CloudTrail-derived policies, then tightening. Say that out loud - it is what people actually do and claiming otherwise is not credible.
- **Data-plane versus control-plane**: an S3 bucket policy and a KMS key policy are separate gates, and a role with `s3:GetObject` and no `kms:Decrypt` fails in a way that confuses people for an hour.

**Depth:** `../05-aws` Categories 1-2; `../11-security` Category 13.

### Q82. VPC: what to draw without hesitation

Must be immediate: the region and its availability zones, public and private subnets per AZ, an internet gateway for public, NAT for private egress, route tables as the thing that actually defines "public", security groups as stateful instance-level rules versus NACLs as stateless subnet-level ones, and where the load balancer and the database sit.

Must be immediate and is often forgotten: **VPC endpoints**, and the reason - gateway endpoints for S3 and DynamoDB are free and keep that traffic off NAT, and NAT data processing charges are one of the most common surprise line items in an AWS bill.

Safe to defer: Transit Gateway topologies, Direct Connect versus VPN specifics, IPv6, PrivateLink for third parties. Say "I would need to look at the specifics" and name what would decide it.

**The one number worth knowing:** cross-AZ traffic is charged in both directions, which is why a chatty service spread across three AZs can have a data-transfer bill larger than its compute.

**Depth:** `../05-aws` Category 3; `../05-aws/core-services` Category 8.

### Q83. "How do you do multi-region?" with the cost visible

Refuse the single answer and give the ladder, with what each rung costs:

| Rung | What you get | What it costs |
| --- | --- | --- |
| Backup and restore to another region | RPO hours, RTO hours | Almost nothing; a plan and a tested runbook |
| Pilot light | RTO tens of minutes | Data replication plus a small standing footprint |
| Warm standby | RTO minutes | Roughly double the data cost, a fraction of the compute |
| Active-active | RTO near zero | Double everything, plus **the real cost: you now have a distributed data problem** |

> "The reason I would push hard on which rung you need is that active-active is not a deployment topology, it is a data model decision. The moment writes happen in two regions, you own conflict resolution, and the honest options are partitioning users by home region so conflicts cannot occur, or accepting last-writer-wins and its data loss, or CRDTs for the small set of things they fit. Most teams that say active-active mean warm standby with a fast DNS failover, and that is usually the right answer."

Add the operational point that is the real killer: **an untested failover is not a failover.** Ask when they last ran one.

**Depth:** `../05-aws` Category 15; `../04-system-design` Category 9.

### Q84. Asked about a service you have never used `[T]`

Bound it, reason from the category, and say what you would check. See Q31 for the general form; the AWS-specific version has one extra move available:

> "I have not used *[X]*. I know the category it sits in - it is *[managed streaming / a queue / a graph database]* - so the questions I would ask are the ones I ask of anything in that category: what are the throughput and size limits, what is the failure mode when I exceed them, what does it cost at my volume, and is it regional or global. What I would not do is put it on a critical path in a design review without having run a load test against those limits, because managed services fail at quotas rather than gracefully."

That last clause is a genuinely senior observation and it converts a knowledge gap into evidence of judgement (Q89).

### Q85. What makes a cost answer credible

**Arithmetic, a dominant term, and a lever.** Vague answers about right-sizing and reserved instances read as a slide.

> "For a service like this the bill is usually three things: compute, data transfer and the managed data stores - and the one that surprises people is data transfer, specifically NAT processing and cross-AZ. So the first thing I do is not optimize, it is **attribute**: tags per service and per environment, and Cost Explorer grouped by that, because you cannot manage what you cannot attribute. Then I look for the dominant term. On the last system I looked at, *[X]* was sixty percent and everything else was noise, so the only conversation worth having was about *[X]*."

Then the levers in order of typical yield: turn off what nobody uses, fix the storage class and retention on data that grows forever, right-size the over-provisioned thing, then commitments (savings plans and reserved capacity) last - because committing to waste locks it in.

**The credibility marker:** naming a percentage split you have actually seen.

**Depth:** `../05-aws` Category 16; `../07-devops` FinOps category.

### Q86. "How do you deploy infrastructure?"

Being probed: whether infrastructure is **code with a review, a test and a state model**, or a console with a wiki page. The tool is nearly irrelevant.

Say the properties first: everything in version control, changes go through review, a plan is produced and read before apply, apply happens from CI rather than a laptop, state is remote and locked, and drift is detected rather than discovered.

Then the tool choice with a real trade-off: "Terraform when there is more than one provider or the team already has it, because the ecosystem and the state model are mature and the language is not fighting me. CDK when the team is strong in one language and the infrastructure is AWS-only and app-adjacent - the abstraction is genuinely productive, at the cost of a compile step producing CloudFormation you then have to debug when it fails. Raw CloudFormation only where something requires it."

**The follow-up that catches people:** "how do you handle a change that Terraform wants to replace rather than update?" Have an answer - plan review as the control, `create_before_destroy`, and the fact that this is exactly why the plan must be read by a human.

**Depth:** `../07-devops` Category 9.

### Q87. Well-Architected without reciting pillars

Use it as a **checklist you run silently** and surface only where it changes a decision. Reciting the six pillars is the tell of someone who has read the whitepaper and not run a review.

> "I have run reviews against it. The way it is actually useful is as a prompt for the questions nobody asked - most designs I review are strong on reliability and have never had a serious conversation about cost or about operational readiness. So the two questions I bring from it are 'what does the on-call person do when this pages' and 'what is the unit cost of this and how does it move with usage'."

Then, if they push: name the pillar relevant to the thing you are discussing, once, and move on. One accurate application beats a complete recitation.

**Depth:** `../05-aws` Well-Architected category.

### Q88. Their architecture has a single-AZ RDS `[T]`

Yes, you point it out - failing to notice is worse than any awkwardness. But **how** you do it is the entire test (Q166).

> "Can I check one thing on the database - is that single-AZ deliberate? … The reason I ask is that a single-AZ RDS has a maintenance and failure window measured in tens of minutes, which would not fit a 99.9 percent target on the read path. If this is a non-production environment or the RTO genuinely allows it, that is a reasonable cost saving and I would leave it."

Three properties: it is a question, not a verdict; it names the specific consequence rather than the label; and it offers a world in which they are right. If they say "yes, we know, it is on the list", the correct response is "makes sense" and move on - relitigating a known trade-off is a negative signal.

### Q89. Quotas and limits: the anecdote

The anecdote should show that you learned quotas are a **design input**, not an operational surprise.

> "We hit the Lambda concurrent execution limit during a replay - the backlog drained faster than steady state, concurrency spiked to the account limit, and the throttling hit an unrelated service in the same account, which is what actually caused the incident. Two lessons: reserved concurrency on the noisy function so it cannot consume the account pool, and a separate account for workloads with burst profiles. Since then, quotas are something I look up during design rather than during an incident, and the ones I check by default are concurrency, per-service TPS on anything with a hard limit, and the ENI and IP limits in the subnet, because that one fails in a way that looks like a networking bug."

**Why it lands:** a blast radius that crossed a boundary, a structural fix rather than a limit increase, and a default practice that came out of it.

**Depth:** `../05-aws` Category 14.

### Q90. Twenty-minute whiteboard architecture review `[A]`

Run it as an inspection with a stated order, so they can follow you (Q164).

Sequence: **ask what it is for and what the constraints are** (two minutes - never critique before this); **trace one request end to end** and find the hops nobody mentioned; **find the state** - where data lives, what is authoritative, what is a cache, and what happens when they disagree; **find the single points of failure and the blast radii**, including account and region boundaries; **check the boring operational things** - deploys, secrets, backups, and whether anyone would know it broke; **then cost**, because it is usually the thing they have not modelled and it is where you can add something they did not expect.

Deliver findings in three buckets, out loud: "one thing I think is wrong, two things I would want to understand better, and one thing I would do differently but would not fight about." That framing is itself the strongest signal in the round - it separates blocking from preference (Q168) and it is what a good staff engineer sounds like in a real review.

### Q91. Justifying a migration to a finance stakeholder `[A]`

Change the vocabulary completely. Not availability zones - **money, risk and time**.

- **Lead with the run-rate comparison including the parts they are already paying but do not see**: data centre, hardware refresh cycle, the people-hours spent on maintenance, the cost of capacity bought for peak and idle the rest of the year.
- **Be honest that lift-and-shift is usually not cheaper**, because that is the claim that destroys credibility six months in when the bill arrives. The savings come from elasticity and from retiring things, and both require work after the move.
- **Quantify the risk you are removing** in their terms: the hardware that is out of support, the recovery time if the data centre is lost today versus after, and the audit findings that go away.
- **Give them a staged commitment**, not a big bang: a first workload with a measurable outcome and a defined spend cap, a decision point, then the rest. Finance stakeholders are far more comfortable with a tranche than a program.
- **Name what could make it a mistake.** "If our load is genuinely flat and our hardware is depreciated, the cost case is weak and we would be doing it for agility, which is harder to put a number on." Volunteering the counter-case is what makes the rest believable.

---

## 7. Data and database round

### Q92. "Write me a query" - what they are reading

Not SQL syntax. They are reading: **do you ask about the schema and the indexes before writing**; do you know what the query will do to the database, not just what it returns; do you handle nulls and duplicates deliberately; and can you explain the join strategy you expect.

The move that scores immediately: before typing, say "let me check my assumptions - is there an index on *[column]*, and roughly how many rows are we talking about? Because at ten thousand rows I would write the readable version and at a hundred million I would write a different query."

Then write the readable version, and say what you expect the planner to do. If you are asked to optimize, that is the second half of the round, and now you have set it up.

**Red flags:** a correlated subquery per row with no comment on it, `SELECT *` in a production example, or `DISTINCT` used to paper over a join that multiplies rows.

**Depth:** `../06-database` Categories 2-3.

### Q93. The three levels of an indexing question

- **Level 1 - what an index is:** a B-tree keyed on the column, so lookups are logarithmic rather than a scan; writes pay for maintaining it. Everyone passes this.
- **Level 2 - composite order, covering and selectivity:** leftmost prefix rule, why `(a, b)` serves `WHERE a = ? AND b = ?` and `WHERE a = ?` but not `WHERE b = ?`; an index that includes the selected columns avoids the heap fetch entirely; and the fact that an index on a low-selectivity column may be ignored because a sequential scan is genuinely cheaper. This level separates most candidates.
- **Level 3 - the planner and the operational reality:** statistics drive the decision, so a stale or skewed distribution produces a bad plan; a function or an implicit cast on the column disables the index; parameter sniffing and plan caching cause the same query to be fast for one input and slow for another; index-only scans depend on the visibility map in Postgres; and every index you add slows every write and inflates the working set, so the right number of indexes on a hot write table is small.

**What each level filters for:** level 2 for people who have tuned a query; level 3 for people who have been paged because of one.

**Depth:** `../06-database` Categories 3-4.

### Q94. "Why is this query slow?" with no schema `[T]`

The test is whether you gather evidence before hypothesizing. Ask in this order, and say why each matters:

1. **"Is it always slow, or slow sometimes?"** Intermittent points at plan variance, lock contention or cache state; always-slow points at the plan or the data volume.
2. **"What does the execution plan say?"** Everything else is speculation until you have looked. Specifically: estimated versus actual row counts, because a large divergence means the statistics are wrong and the plan is built on a lie.
3. **"How many rows does it examine versus return?"** The ratio is the whole diagnosis.
4. **"When did it change, and what changed then?"** Data growth crossing a threshold, a deploy, a new index, an analyze.
5. **"Is it slow, or is it waiting?"** Locks and connection-pool queueing look identical from the application side and have nothing to do with the query.

**The point to make explicitly:** the fifth question catches the case where the query is fine and the problem is elsewhere, which is common enough that jumping straight to query tuning is the most expensive mistake in this genre.

### Q95. Transactions and isolation without the anomaly table

Answer with **the decision you actually make**, and let the theory support it.

> "In practice I run read committed, which is the default nearly everywhere, and I handle the anomalies explicitly where they matter rather than raising the isolation level globally. The two that bite are lost update - two transactions read, modify and write the same row - and the read-modify-write pattern generally. My default fix is not serializable, it is to make the write atomic in the database: `UPDATE ... SET balance = balance - ? WHERE id = ? AND balance >= ?` and check the row count, or an optimistic version column and a retry on conflict. I reach for `SELECT ... FOR UPDATE` when I genuinely need to hold a row, and for serializable when the invariant spans multiple rows and cannot be expressed as a constraint - accepting that it means handling serialization failures and retrying."

**The senior markers:** preferring a constraint or an atomic statement over a lock, knowing that higher isolation means your application must handle retries, and knowing that MVCC readers do not block writers, which is why the naive mental model of locking is wrong on Postgres.

**Depth:** `../06-database` Category 5.

### Q96. SQL versus NoSQL without religion

Take a position, make it conditional, and make the criterion **access patterns and the shape of the truth**, not scale.

> "My default is a relational database, because most systems have relationships, most teams can hire for SQL, and the constraint system does correctness work you would otherwise write and test yourself. I move off it when there is a specific reason: an access pattern that is genuinely a single-key lookup at a volume where a partitioned key-value store is dramatically simpler; a document shape that has no stable schema and is never queried across; a write volume that no single primary can take, where the sharding is going to happen anyway and a store that does it natively beats one where I do it by hand. What I try hard to avoid is choosing a document store because the schema is not designed yet - that is not a technology decision, it is deferring one."

Then the honest cost of each direction: relational gets painful when you must shard, and a key-value store gets painful the first time the business asks a question you did not design a key for.

**Depth:** `../06-database` Category 9.

### Q97. "How would you shard this?" - what comes first

Three things must be established before an answer is meaningful, and saying so is the answer:

1. **Are you sure you need to?** "The largest single Postgres I have seen handle real workloads goes a long way with a read-replica fleet, partitioning and an archive strategy. Sharding is the last resort because it costs you cross-shard queries, transactions and joins forever. What is the actual constraint - write throughput, data size, or blast radius?"
2. **What is the access pattern?** The shard key is determined by the dominant query, not by what looks balanced. Sharding by tenant is right when queries are always within a tenant, and wrong the day the biggest tenant is ten percent of your data.
3. **What happens to the queries that cross shards?** Every design has some. Name them and say whether they become a fan-out with a merge, a denormalized secondary index, or an analytics copy.

Then the mechanics: hash versus range, the resharding problem and why consistent hashing or a large fixed number of logical shards mapped to physical ones is how you avoid a migration nightmare, and how you route.

**Depth:** `../06-database` Category 7.

### Q98. Caching proposed for a write-heavy problem `[T]`

Redirect by asking for the number, not by contradicting.

> "Possibly - can I check the read-write ratio first? … If it is closer to one-to-one, a cache is going to be mostly misses and mostly invalidation, and we will have added a consistency problem without buying much. What I would look at instead for a write-bound workload is *[batching the writes, moving them off the request path onto a queue, checking whether the cost is actually index maintenance, or a write-optimized store]*. If there is a hot read set inside this - say the same thousand rows are read constantly - then a cache in front of that specific path is worth it, and we can measure that from the query stats."

**The structure:** a question that produces the disconfirming number, the mechanism explaining why the instinct fails, an alternative, and a version of their idea that would work. That last part matters - people accept redirection much better when part of their suggestion survives.

### Q99. Live schema migration - the detail that proves it

The proof is knowing that the **deploy sequence is the migration**, and that it is more than one release.

> "Expand and contract, and it is at least three deploys. Deploy one adds the new column, nullable, with no constraint - and if the table is large I add the index concurrently, because a plain `CREATE INDEX` takes a lock that will take the site down. Deploy two writes both old and new, and backfills in batches with a sleep between them, watching replication lag - the backfill is the part that causes the incident, not the DDL. Deploy three reads from the new column. Deploy four stops writing the old one, and only much later do I drop it, because the rollback of deploy three has to be possible for a week, not for an hour."

**The specific details that mark experience:** `CREATE INDEX CONCURRENTLY`, batching with a lag check, adding a `NOT NULL` constraint as `NOT VALID` and validating separately, a lock timeout on the DDL so a migration cannot queue behind a long transaction and block everything, and the fact that the drop happens weeks later.

**Depth:** `../06-database` Category 12.

### Q100. The replication lag anecdote

Needs a number, a user-visible symptom, and a fix that is not "add more replicas".

> "We had users creating a record and then getting a 404 on the redirect, at maybe one in fifty. The reads were going to a replica and the lag was normally under twenty milliseconds but spiked to several seconds during the nightly batch. Two fixes: read-your-own-writes routing, so a request from a user who has written in the last few seconds goes to the primary, and separately we moved the batch off the primary. The permanent change was that lag became an SLI with an alert, rather than a number someone looked at during an incident."

**What it demonstrates:** you know lag is a correctness problem and not a performance problem, you know the routing fix (Q56), and you found the cause of the lag rather than tolerating it.

### Q101. "How big can PostgreSQL get?" `[T]`

There is no correct number, and the interviewer knows. They are testing whether you **reframe into the variables** rather than guessing.

> "I would not answer in terabytes, because the limit is never the size - it is the workload. The things that actually break first, roughly in order: write throughput on a single primary, because there is one; the working set no longer fitting in memory, at which point the p99 changes character rather than degrading smoothly; vacuum and bloat on a high-churn table; index maintenance on wide tables; and the operational limits - how long a restore takes, how long a major version upgrade takes, how long an index build takes. I have seen single instances in the multi-terabyte range work perfectly well because the hot set was small and the writes were modest, and I have seen a two-hundred-gigabyte database in trouble because it was write-hot with six indexes."

Then the number that is actually useful: "the question I would ask instead is what your write rate and your hot-set size are, because those two tell me whether you have a problem."

### Q102. Live modeling: subscription billing `[A]`

The scoring is on whether you recognize the **domain's genuine hard parts** rather than producing tables.

Get these on the board and you have passed: a **subscription** with a plan and a lifecycle (trialing, active, past due, cancelled, and the difference between cancelled-now and cancel-at-period-end); **price versus plan versus subscription** - prices change and existing subscriptions must not, so a subscription references a price version rather than a plan; **the invoice as an immutable document** with line items, separate from the subscription state; **money as an integer of minor units with a currency**, never a float, said explicitly; **proration** as the hard part - what happens on a mid-cycle upgrade, and the fact that this is where every billing system's bugs live; **payment attempts as their own entity** with a retry schedule, because a payment is a process, not a field; and an **event log**, because billing disputes are resolved by history and "what did we think was true on the 14th" is a question you will be asked.

**The sentence that shows you have done it:** "the invariant I would defend hardest is that an invoice, once issued, never changes - corrections are credit notes. Every billing system that mutates invoices ends up unable to answer an auditor."

### Q103. Five datastores in ten minutes `[A]`

Two minutes each. The structure for each: **the dominant access pattern in one sentence, the choice, the reason, and the thing you are giving up.** Do not hedge - the round is testing decisiveness under time pressure, and a defended wrong-ish choice scores better than five "it depends".

A worked example of the cadence: "Session state: single-key read and write, high volume, short-lived, loss is tolerable because it means a re-login. Redis or DynamoDB with a TTL; I would take DynamoDB if I did not already run Redis, because there is nothing to operate. Giving up: nothing much, this is the easy one."

Then keep the same rhythm for the others - a transactional core (relational, and say why not something else), an audit or event log (append-only, cheap object storage plus a query engine, or a log), a search or analytics workload (an inverted index or a columnar store, and the fact that it is a *copy*, never the source of truth), and a high-volume time series (a purpose-built store with downsampling and retention, because the retention policy is the design).

**The closing line that scores:** "four of those five are copies of, or subordinate to, one authoritative store - I would want to be very clear which one is the source of truth, because that is the decision that survives all the others."

### Q104. One database story across three rounds

Use different **layers** of the same incident, and say the connecting sentence out loud only if the interviewers overlap.

- **Design round:** the story appears as a *constraint that shaped the architecture* - "we knew the read path could not touch the primary, which is why the fanout is precomputed."
- **Deep-dive round:** the same incident appears as *mechanism* - the lag, the routing, the isolation level, in detail.
- **Behavioral round:** the same incident appears as *how you led it* - who you got in the room, the call you made with incomplete information, what you changed organizationally afterwards.

**Why this is better than three separate stories:** depth. An interviewer who hears three shallow stories learns less than one who hears three faces of one deep one, and the panel comparing notes sees consistency rather than repetition (Q182).

**The one risk:** if two interviewers hear the *same* face, it reads as a script. So label the face you are giving: "I have talked about the architecture of this with your colleague - I will focus on how we ran the incident."

---
## 8. DevOps, delivery and incident-command round

### Q105. "Walk me through your CI/CD pipeline"

Expected detail: the **stages, the gates, and what stops a bad change** - roughly ninety seconds, then depth on request.

> "Commit to trunk triggers build and unit tests, then static analysis and a dependency and secret scan, then the artifact is built once and signed - and that same artifact is what goes to every environment, which matters more than it sounds because rebuilding per environment means you never tested what you shipped. Integration tests run against ephemeral dependencies, then deploy to staging automatically, run the smoke suite, and production is a promotion of the same artifact behind a progressive rollout with automated rollback on the error-rate SLI."

**Where candidates stop too early:** they describe build and test and stop at "then it deploys". The interesting half is everything after the artifact - promotion, environment configuration as a separate input, database migrations relative to the deploy (Q99), rollback, and how a failed deploy is detected without a human watching.

Have one number ready: lead time, deployment frequency, or the duration of the pipeline.

**Depth:** `../07-devops` Categories 1-3.

### Q106. Structure of an incident-command answer

CIDER maps onto it, but weight it differently from a design answer: the interviewer wants **command**, not debugging.

- **Clarify** becomes *establish*: who is incident commander (say "I took command" or "I handed command to X and took the technical lead" - the distinction is the whole signal), what the customer impact is in one sentence, and what the severity is.
- **Isolate** becomes *stabilize before diagnose*: what did you do to stop the bleeding before you understood the cause? Roll back, fail over, shed load, disable the feature. A candidate who diagnoses first while customers are down is describing debugging, not incident command.
- **Decide** is the call you made with incomplete information, and the fact that you made it - with the time on the clock.
- **Execute** includes communications: who you told, how often, and what you said to a stakeholder who wanted an ETA you did not have.
- **Reflect** is the blameless review and, critically, **whether the action items were actually done**.

**The line that separates senior from principal:** "the fix stopped that outage; what I actually changed was *[the class of failure]* so it could not recur, and here is how I knew it worked."

### Q107. "What was your worst outage?" `[T]`

Take **real ownership of a decision**, not of everything and not of nothing.

Too little blame - "the vendor had an outage", "a colleague pushed a bad config" - reads as someone who will not be accountable. Too much - "it was entirely my fault, I should have caught it" - reads as either performative or as poor judgement about systems, because at principal level a single person's mistake causing a major outage **is a systems failure**.

The calibrated version:

> "I own two things in it. I approved the change, and my review missed that the migration held a lock; that is on me and I would review differently now. The bigger thing I own is that the system allowed it - there was no lock timeout and no canary on the migration path, and I had known about that gap for months and not prioritized it. What I changed afterwards was the second one."

**The structure:** a specific personal error, a systemic gap you were responsible for, and a fix aimed at the system. Name the impact honestly with a number, do not name individuals, and do not describe the vendor or a colleague as the cause even when they were.

### Q108. DORA without sounding like a consultant

Use the metrics as **diagnosis**, never as a scorecard you recite.

> "I use them as a pair of ratios rather than four numbers. Deployment frequency and lead time tell me how big a batch is; change failure rate and recovery time tell me what a batch costs when it is wrong. The useful insight is that they move together - teams deploy rarely *because* deploys are dangerous, so the batch gets bigger, which makes them more dangerous. The intervention is almost never 'deploy more often', it is to make a deploy cheap to reverse, and then frequency moves on its own. On one team, lead time was nine days and almost all of it was waiting for a manual regression sign-off - so the fix was test automation, not process."

**Red flags:** quoting the elite-performer thresholds as targets, or presenting the four metrics as a maturity model. Both read as having read the book rather than moved a number.

**Depth:** `../07-devops` Categories 1 and 10.

### Q109. Kubernetes when you are not a specialist

Draw the line **explicitly and by layer**, then be genuinely strong on your side of it.

> "I will tell you where my line is. I am solid on the application-facing model - deployments, services, ingress, config and secrets, requests and limits, probes, rolling updates and pod disruption budgets, and how a rollout actually replaces pods. I can debug why a pod is not receiving traffic or why it is being OOM-killed. Where I am not the expert is the cluster layer - CNI internals, etcd tuning, upgrade choreography, custom operators. On my teams that has been a platform function, and my job has been the contract between the app teams and that platform rather than running the cluster."

That answer is honest, bounded and still substantial. The follow-up will usually be on your side of the line, so make sure the app-facing depth is real: what a readiness probe does during a rollout, why a memory limit behaves differently from a CPU limit, and what a pod disruption budget prevents during a node drain.

**Depth:** `../07-devops` Categories 4-5.

### Q110. "How do you roll back?" - three levels

- **Level 1:** redeploy the previous artifact. Fine, and everyone says it.
- **Level 2 - what makes it possible:** the previous artifact still exists and is deployable; configuration is versioned with it; the rollback path is exercised regularly rather than theoretically available; and the decision to roll back is automated on an SLI rather than debated in a call at 3am.
- **Level 3 - what makes it impossible, which is the real question:** a database migration that dropped a column; an event schema change consumers already adopted; a cache or a data format written in the new version that the old one cannot read; a feature that has already sent emails. So the durable answer is that **rollback is a design constraint, not a procedure**: expand-and-contract migrations (Q99), backwards-compatible message schemas for at least one version, and feature flags so the *behaviour* can be reverted without reverting the *deployment* - which is faster and safer, because the code path being reverted was already running.

**The sentence that lands:** "the question I ask in design review is not 'can we roll back', it is 'what is the first hour in which we no longer can'."

### Q111. On-call questions are leadership questions

They are asking: **do you take responsibility for the operational consequences of what you build, and do you improve life for the people carrying the pager?**

The answer therefore has three parts: that you carry it ("I have been in the rotation at every level, including now"); how you treat the load as a metric rather than a fact of life - pages per shift, percentage actionable, percentage out of hours, and what you did when it was bad; and a specific instance where you **deleted alerts** or fixed the underlying cause rather than writing a better runbook.

> "The rotation was getting about eleven pages a week and roughly half were not actionable. We audited every alert against one rule - does a human need to do something in the next fifteen minutes - and deleted or downgraded everything that failed it. That took us to three a week, and the important part is that the remaining ones started getting taken seriously again, which is the actual damage that noisy alerting does."

**Depth:** `../07-devops` Category 11.

### Q112. "How would you improve our deployment process?" `[T]`

The trap is answering. You have one sentence of context and a confident recommendation will be wrong, patronizing, or both.

> "I would want to ask a few things first, because the same symptom has very different causes. What is the lead time from merge to production, and where does it actually go? Is the delay technical or is it waiting for a person? What is your change failure rate - if it is low and you deploy slowly, the process may be fine and expensive; if it is high, speed is not the problem. And what has been tried?"

Then, having earned it, offer a **direction rather than a solution**: "if it is mostly waiting for a manual gate, the highest-yield work is usually making rollback cheap enough that the gate is no longer justified, rather than optimizing the gate."

**What is being scored:** whether you diagnose before prescribing. It is the same test as Q94 and Q170, and interviewers use it because consultants and senior engineers fail it constantly.

### Q113. Observability beyond a list of tools

A strong answer is about **what questions you can answer**, and about the discipline rather than the stack.

- **The three signals with distinct jobs**: metrics tell you something is wrong and are cheap and aggregate; traces tell you where in a distributed path; logs tell you why, for one specific request. A team that logs everything and has no metrics cannot detect, and a team with metrics and no traces cannot localize.
- **Cardinality as the cost model.** High-cardinality identifiers belong on spans and logs, never on metric labels (Q57).
- **Correlation** - a trace id propagated into logs and surfaced in the error the user sees, so a support ticket is one query rather than an investigation.
- **SLOs as the thing you alert on**, so pages are user-impacting by construction, plus error budgets as the mechanism that converts reliability into a prioritization conversation rather than an argument.
- **The honest gap:** what could break right now without any of this noticing? Naming your own blind spot is the most senior thing you can say here.

**Depth:** `../07-devops` Category 8.

### Q114. Secrets management under a security follow-up

Survives scrutiny: secrets are **never in the repository, never in the image, never in an environment variable printed by a crash dump**; they are fetched at runtime from a manager with an identity the workload already has (an IAM role, a service account), so there is no bootstrap secret; access is audited; and rotation is automatic and **tested by actually rotating**, because a rotation path that has never run does not work.

Then the two follow-ups a security interviewer will ask, and you should pre-empt one:

- **"How would you know if one leaked?"** Detection: secret scanning in CI and on the whole history, canary credentials, and anomaly detection on the audit log. And a rehearsed revocation path, because the response to a leak is revoke-then-investigate.
- **"What about the developer laptop?"** Local development uses a separate, lower-privilege credential set, never production values, and this is the gap in most organizations.

**The honest admission that helps:** environment variables are the common compromise and they are weaker than a runtime fetch - say which one you actually did and why.

**Depth:** `../11-security` Category 9.

### Q115. Canary versus blue-green, specific to their constraints

Do not compare the two in the abstract. **Name the constraint that decides it.**

> "It comes down to three things. First, can you run both versions against the same data at the same time? If a schema or a message format change makes that unsafe, canary is out until the change is made compatible - that constraint decides more of these than anything else. Second, do you have a signal fast enough to judge a canary? If your quality metric takes an hour, a ten-minute canary tells you nothing and blue-green with a fast rollback is more honest. Third, what does a bad request cost - blue-green exposes a hundred percent of traffic to the new version for however long it takes to notice, so for high-value irreversible operations I want gradual exposure even if it is slower."

Then land it: "given a stateless service with a good error-rate signal, canary. Given a database-coupled deploy with a slow signal, blue-green with a tested rollback and a smoke suite."

**The extra credit:** mention that neither helps if the change is behind no flag and has already written data (Q110).

### Q116. "We deploy once a quarter and it works for us" `[T]`

Do not challenge the frequency. **Ask about the consequences**, and let them draw the conclusion - and be prepared for the possibility that they are right.

> "That is workable in some contexts - what does a hotfix look like when you need one? … And how long does the quarterly release take from cut to done, and how often does it need a fix afterwards?"

If the answers are "hotfixes take a day and go out fine" and "the release is smooth", they have a working system with a large batch size and low change rate, and the correct response is to say so. Regulated, embedded and vendor-shipped software genuinely lives here.

If the answers are "hotfixes are terrifying" and "the release takes a week and always needs two follow-ups", the diagnosis says itself and you have not had to accuse anyone of anything: "then the thing I would look at is not the frequency, it is that the batch is large enough that you cannot attribute a failure to a change."

**What is scored:** that you did not apply a best practice to a context you had not investigated (Q112).

### Q117. Live incident simulation `[A]`

Run as a full CIDER walkthrough in [scenario-questions.md](scenario-questions.md), Part A. The behaviours the simulation is scoring:

- **You declare and take command in the first minute**, and you say the customer impact out loud before touching a dashboard.
- **You ask for the timeline** - what changed, when did it start, do they correlate - before proposing a cause.
- **You mitigate before you diagnose** where mitigation is available, and you say that is what you are doing.
- **You state hypotheses as falsifiable** and say what evidence would discriminate, rather than pursuing one theory.
- **You communicate on a cadence** and you say what you will do if the current line of investigation fails.
- **You do not go quiet.** Silence while thinking is the most common failure in this round; narrate.

### Q118. A platform team's charter and metrics `[A]`

The charter, in one sentence they can repeat: *"we make the paved road the fastest way to production, and we own the things every team would otherwise build badly."* Then the parts that make it real:

- **Product, not policy.** Adoption must be voluntary and won on merit. A platform that mandates gets routed around, resented, and eventually replaced. The corollary is that the platform team has users and needs a roadmap, support and a feedback loop.
- **Scope by cost of duplication**: deployment, observability wiring, service templates, secrets, identity, cost attribution. Not: business logic, and not everything that is technically shared.
- **An escape hatch by design.** Teams must be able to leave the road, and those cases are your backlog rather than your enemy.

Metrics, and be careful with them: **time from empty repository to a service in production**, **adoption as a percentage of eligible teams**, **change failure rate for road users versus non-users** (the honest one - if the road is not safer, it has no case), and **support load per adopting team**, which should decline. Explicitly reject "number of services migrated" as a target, because it drives migration over value.

**The trade-off to volunteer:** a platform is a coupling. Every team on it inherits your outages and your release cadence, and that has to be earned continuously.

---

## 9. AI round: GenAI, RAG and agents

### Q119. "What have you actually built?"

The structure that survives skepticism: **one system, in detail, with numbers on both quality and cost, plus one thing you refused to build.**

> "Concretely, *[a retrieval-grounded assistant over X documents for Y users]*. The parts I own the reasoning for: chunking and the ingestion path, hybrid retrieval with a reranker, the context assembly under a token budget, and the evaluation set - about *[n]* cases built from real production queries, scored on retrieval recall and on answer groundedness, run in CI on every prompt or model change. Cost is *[figure]* per query at *[figure]* per month, and the dominant term was *[X]*, which we cut by *[Y]*. The thing I would also mention is what we decided not to do: *[the agentic version]*, because *[the reason]*."

**Why the refusal matters more than the build:** at principal level in AI, judgement about scope is the scarcest signal (`../10-ai-agents` Q3). Everyone has shipped a chatbot; very few have argued one down.

**Red flags:** framework names as the substance, no evaluation, no cost figure, and "we use RAG" as if it were a design.

### Q120. Separating GenAI, RAG and agents out loud

State the boundaries in three sentences, unprompted, early in the round. It immediately positions you above the candidates who treat it as one topic.

> "I keep three things separate. **The model** is a component with a context window, a decoding behaviour, a latency profile and a price - and its behaviour under those constraints is one body of knowledge. **Retrieval** is an information system: ingestion, chunking, indexing, hybrid search, reranking and permissions - it is mostly a search problem, and most 'the LLM is wrong' bugs are actually retrieval bugs. **An agent** is the system around the model, where the model chooses the control flow at runtime - and that is a distributed systems and authorization problem, not a prompting one. They fail differently and you debug them differently, which is why the distinction is worth making."

**Follow-up you are inviting and want:** "so how do you tell whether a bad answer is a retrieval failure or a generation failure?" Answer: check whether the correct chunk was in the context. If it was not, it is retrieval; if it was, it is generation. That single diagnostic is the most useful thing in the domain and it is the answer to Q124 too.

### Q121. "Isn't this all just prompt engineering?" `[T]`

Concede the true part immediately, then relocate the work. Defensiveness confirms their suspicion.

> "The prompt is real but it is the smallest part, and it is the part that stops mattering as models improve. The engineering is everywhere else: what goes into the context and how it was selected, which is a retrieval and ranking problem; the token and cost arithmetic; the evaluation harness, because without one you cannot change anything safely; the failure behaviour, including when the system should decline to answer; and the authorization boundary once the model can call tools. Concretely, on the last system, prompt changes accounted for a small share of the quality improvement - the improvement came from the retrieval and the reranking. And the reason I care about that distinction is that prompt work does not compound and the rest does."

**The strongest evidence** is an anecdote where a better prompt did not fix it and something structural did.

### Q122. Token and cost arithmetic in your head

Carry these and be able to say them without hesitation:

| Quantity | Rule of thumb |
| --- | --- |
| Tokens per word (English) | ~1.3, so 750 words ≈ 1,000 tokens |
| A page of text | ~500-800 tokens |
| Cost of a call | (input tokens × input price) + (output tokens × output price), and **output is several times more expensive per token** |
| Attention cost | quadratic in sequence length - doubling the context roughly quadruples that term |
| Cached input | typically around a tenth of the price, and only for a stable prefix |
| An agent loop's total input | ≈ `n·b + s·n²/2` for n steps, base b, per-step growth s |

The way to use it in a round:

> "Say 3,000 tokens of context and 500 out, at *[prices]* - that is roughly *[X]* cents a call. At 100,000 calls a day that is *[Y]* a month, which is the number that decides whether we cache aggressively or accept it. And since output tokens dominate the per-call cost, the cheapest quality win is usually shortening the answer, not the prompt."

**What scores is doing it out loud and reaching a decision from it.** The precision does not matter; the habit does.

**Depth:** `../08-genai` Categories 2 and 13.

### Q123. The first five decisions in a RAG design round, in order

1. **Is retrieval the right answer at all?** If the corpus is small enough to fit in context, or the questions are aggregations better served by a query, say so. This is the question nobody asks and it is the strongest opener.
2. **What is the unit of retrieval?** Not "how do I chunk" - what is the smallest thing that is independently meaningful and answers a question? Chunk size falls out of that, and the document structure drives it more than a token count.
3. **What is the query, really?** Are users asking lookup questions, comparison questions or aggregations? Retrieval only serves the first well, and naming that early prevents designing a system that will fail on a third of the traffic.
4. **The retrieval strategy**: hybrid by default - lexical for names, ids and exact terms, dense for paraphrase - with a reranker over a wide candidate set, because the reranker is usually the single highest-yield component.
5. **Permissions**, and it must be at this point rather than later, because filtering after retrieval breaks recall and filtering before it changes the index design. If different users must see different subsets, that is an architectural input, not a feature.

**Then, immediately:** evaluation (Q125) and what happens when retrieval returns nothing good (Q126).

**Depth:** `../09-rag` Categories 2-10.

### Q124. Diagnosing a poor-quality RAG system with three questions `[T]`

- **"When it gives a bad answer, was the right document in the context?"** This is the whole diagnosis and almost nobody has checked. If not, it is a retrieval problem and prompt work is wasted. If it was, it is a generation, context-assembly or ordering problem.
- **"How do you know it is bad - what is your eval set and where did the cases come from?"** If the answer is "users complain", the real problem is that they cannot measure, and nothing else can be fixed until that is true.
- **"What does it do when it does not know?"** If it always answers, they have no abstention path, and a large share of the perceived quality problem is confident answers to unanswerable questions.

Then, if they are still talking, the two mechanical causes that account for most cases: **chunking that split the answer across a boundary**, and **no reranking**, so a top-5 from an embedding search is being handed to the model with the right chunk sitting at rank 12.

**Why this scores:** three questions, each of which discriminates, and you did not propose a fix before diagnosing.

### Q125. "How do you evaluate it?" - the complete answer

Cover four layers; most candidates give one.

- **The dataset.** Where the cases came from - real production queries, not invented ones - how many, who labelled them, and how it is kept from becoming a training set you have overfitted to.
- **Retrieval, separately from generation.** Recall at k on whether the correct chunk was retrieved at all. This is a cheap, objective, deterministic metric and it isolates half the system (Q120).
- **Generation.** Groundedness (is every claim supported by the retrieved context), correctness against a reference where one exists, and refusal behaviour on unanswerable questions - which must be in the set, or you will optimize for a system that never says no. LLM-as-judge is usable for groundedness *if* the judge is itself validated against human labels on a sample.
- **The gate and the operations.** It runs in CI on every prompt, model or index change; the release criterion covers cost and latency as well as quality; and online, you track user-visible proxies - thumbs, escalation rate, follow-up rate - because the offline set will not predict everything.

**The sentence that closes it:** "the point of the harness is not the score, it is being able to change something and know within twenty minutes whether it made things worse."

**Depth:** `../08-genai` Category 10; `../09-rag` Category 11.

### Q126. Hallucination with mechanism, not reassurance

Start with what it *is*, because the mechanism dictates the controls:

> "The model is sampling a plausible continuation; it has no representation of 'I do not know this'. So fluency and correctness are independent, and the fix is not to ask it to be accurate. There are three places to intervene. **Before**: ground it - put the answer in the context, and if retrieval found nothing above a relevance threshold, do not call the model at all, return the no-answer path. **During**: constrain what it can produce - a schema, an enum, an id that must exist. **After**: verify - check that every claim is supported by the retrieved text, check that cited ids exist, and for anything actionable, validate against the system of record before it reaches the user."

Then the honest bound, which is the credibility move: "none of that eliminates it. It reduces the rate and, more importantly, makes the remaining cases *detectable*. So the design question I actually care about is what happens when it is wrong - if a wrong answer is silent and consequential, no accuracy figure makes that architecture acceptable."

**Depth:** `../08-genai` Category 11; `../09-rag` Category 12.

### Q127. "Do not build an agent" - and how to say it

Be for something rather than against their idea. The persuasive form is a **comparison they can check**.

> "Let me ask five things first: can you draw this process as a flowchart today; how many genuinely distinct paths are there; are the actions reversible and reviewed; can you write fifty test cases right now; and what is your cost tolerance at the ninety-ninth percentile? … Given those answers, I would build a router plus four workflows, and keep one narrow agentic path for the residue that does not fit. It costs a fraction as much, you can test every path, and when it is wrong you can point at the branch. The place I would spend the agent budget instead is *[the hard part that is actually hard]*."

**The tone that works with someone invested in the agent:** you are not saying agents are bad, you are saying the lowest rung of the autonomy ladder that solves the problem is the right one, and you are offering to be wrong - "if the paths turn out not to be enumerable, that is exactly when I would change my mind."

**Depth:** `../10-ai-agents` Categories 1 and 7.

### Q128. "What model do you use?" `[T]`

The answer is a **selection process and a swap cost**, because any model name you give is out of date and reveals nothing.

> "I would rather answer with how we choose, because the specific model has changed three times in the last year and will change again. We pick per task, not per product: the classification and extraction steps use a small fast model, the synthesis step uses a larger one, and we re-run the eval set whenever a candidate appears. The important architectural property is that the model is behind an interface with the eval harness attached, so switching is a configuration change plus a test run rather than a project. Right now the mix is *[X]* for *[reason]* - but the reason is the answer, not the name."

Then the criteria that show you have actually done it: quality on *your* eval set rather than a public benchmark, latency at p95, cost per task, data residency and retention terms, and whether you are exposed to a provider deprecating a version underneath you.

### Q129. Raising prompt injection without derailing

Raise it **once, precisely, tied to a specific capability in the design**, then offer to come back.

> "One thing I want to flag on this component rather than dwell on: the moment this reads content a user or a third party controls and it also holds a tool that can write or send, the injection risk becomes an authorization problem rather than a content-filtering problem. The control I would put in is that the tool's permissions come from the *user's* identity and are enforced in code outside the model, so the worst case is bounded by what that user could do anyway. Happy to go deeper if it is useful, otherwise I will keep moving."

**Why this works:** it is fifteen seconds, it names the mechanism, it proposes a structural control rather than a filter, and it hands the interviewer the choice. Compare with the failure mode, which is a five-minute security digression in a design round.

**What not to say:** that you would sanitize the input or add a classifier as the primary control. That answer marks you as answering the 2023 version of the question.

**Depth:** `../10-ai-agents` Category 13; `../11-security` Category 12.

### Q130. AI from 2024 as depth, not a pivot

Two moves. First, **claim depth on a bounded surface** rather than breadth on all of it: "I am not an ML researcher and I do not train models. What I am is a systems engineer who has taken LLM features to production, and the hard parts there have been retrieval quality, evaluation, cost and the authorization boundary - which are all problems I have nineteen years of context for."

Second, **connect it to the older work explicitly**, because that is what turns two years into nineteen: an evaluation harness is a test strategy for a nondeterministic system; context assembly under a token budget is a caching and selection problem; agent durability is sagas and idempotency (`../03-microservices`); tool authorization is the confused deputy problem. Saying one of those out loud reframes the recency entirely.

**The trap** is overclaiming into research territory. One question about model internals you cannot answer, after you have positioned yourself as an AI expert, costs more than the modest framing would have.

### Q131. When Java and Spring AI helps, and when it does not

**Helps** when the role is enterprise integration: the AI capability has to live inside an existing Java estate with its transactions, security and observability, and the interviewer's real problem is how to get an LLM feature into a regulated Spring Boot system without a second stack. There, knowing `ChatClient`, advisors, tool callbacks and where the abstraction leaks is a genuine differentiator, and so is the operational argument - one deployment story, one identity model, one set of dashboards.

**Reads as a limitation** when the team is a Python AI shop. Bringing it up unprompted there suggests you would fight the ecosystem. The correct framing is portability: "the architecture I care about is the same in either language - the model behind an interface, retrieval as a service, the eval harness in CI. I have implemented it in Java; the Python ecosystem has more tooling for the experimentation half and I would use it."

**The judgement being tested:** whether you would impose your stack on a team where it is the wrong fit.

**Depth:** `../02-spring` Spring AI category; `../10-ai-agents` Category 17.

### Q132. The interviewer is more current than you `[T]`

Do not compete on recency; you will lose and it is not what is being scored. **Move to the axis where your experience is the advantage** - and be visibly interested in what they know.

> "You are ahead of me on that - I have not used it. What I would want to know before putting it in a system is whether it changes any of the constraints I design around: does it change the cost per task by an order of magnitude, does it change the latency profile, and does it remove a failure mode or just shrink it. Those are the three things that would make me redesign rather than swap. Has it changed any of those for you?"

That response does four things: it concedes honestly, it demonstrates a durable framework, it shows you evaluate rather than adopt, and it makes them talk - which they want to do, and which converts the round into a conversation between peers.

**The general principle:** in a field that churns quarterly, **the mechanism and the evaluation discipline are what you are being hired for**, and saying so explicitly is legitimate.

### Q133. An AI capability with a 300 ms budget `[A]`

The first move is to establish that **a large model call is not in the budget** and therefore the design question is what can be moved off the synchronous path.

Work the arithmetic out loud: time to first token for a large model is typically hundreds of milliseconds before any generation, and full generation of a paragraph is seconds. So within 300 ms end to end, including retrieval and network, a general-purpose model call on the critical path is out.

Then the options, with what each costs: **precompute** - do the model work ahead of time and serve a lookup, which works for a bounded input space (embeddings, classifications, summaries per document) and fails for open-ended input; **a small specialized model** - a distilled classifier or an embedding model, tens of milliseconds, at the cost of generality; **cache the model's output** on a semantic or exact key, with the honest note that hit rate decides whether this is a solution or a decoration; **stream and change the UX contract**, so 300 ms to *first token* is achievable even when completion is not - and check whether the requirement is really end-to-end or perceived latency, because it usually is not what the ticket says; **make it asynchronous**, showing a non-blocking result and filling in.

**The strong close:** "I would push back on the requirement once, with data - if the answer is that 300 ms is a hard product constraint on the whole response, then the honest design is a small model or a precomputed lookup, and we should scope the feature to what that supports rather than pretend."

**Depth:** `../08-genai` Categories 13-14; `../04-system-design` Category 11.

### Q134. AI engineering standards for 300 engineers `[A]`

Standards that are documents get ignored, so answer in terms of **what is paved, what is gated, and what is measured**.

- **Paved road:** one approved way to call a model - a gateway that every team uses, which gives you central key management, per-team cost attribution and quotas, request and response logging for evaluation, retries and fallbacks, and the ability to change providers once for everyone. This single piece of infrastructure is worth more than every policy document.
- **Gates, and only where the risk justifies them:** no LLM output reaching a user-visible or system-changing path without an eval set in CI; a review for anything that gives a model a tool with write access; and a data classification check before a corpus is indexed.
- **Defaults in a template:** a starter with the gateway client, tracing, a cost budget per request, prompt and model versions pinned as configuration artifacts, and an eval harness scaffold - so the right thing is the easy thing.
- **Measured:** spend per team, eval coverage on production paths, and incidents attributable to AI components.
- **Explicitly not standardized:** prompts, model choice per task, and the experimentation stack. Standardizing those is where platform teams lose their users.

**The organizational sentence:** "I would start with the gateway and the eval requirement, because those two give you leverage over everything else. Trying to publish comprehensive standards before either exists produces a document nobody reads."

---

## 10. Security round

### Q135. "How do you secure an API?" in 90 seconds

Answer in **layers, outside in**, one clause each - the structure is the signal.

> "Transport: TLS everywhere including internally, HSTS, and no exceptions for internal traffic because the network is not a boundary. Identity: OAuth 2.1 or OIDC with short-lived access tokens validated locally against cached JWKS, checking issuer, audience, expiry and signature algorithm explicitly. Authorization: enforced per resource at the service, not at the gateway, and never derived from anything the client sent. Input: validated against a schema, parameterized queries, output encoding at the point of rendering. Abuse: rate limits per identity rather than per IP, quotas, and payload size caps. Data: field-level control over what is returned, so the object you serialize is a response model rather than your entity. Operations: audit logging of authorization decisions, dependency scanning, and secrets from a manager. If I had to pick the one that fails most often in the systems I have reviewed, it is authorization at the object level."

**That last sentence is the differentiator** - it shows you have reviewed real systems rather than memorized a checklist.

**Depth:** `../11-security` Categories 4-7.

### Q136. OAuth and OIDC: what you must know cold

**Without notes:** the difference between authentication and authorization and which protocol does which; authorization code flow with PKCE and why it replaced implicit; what the access token, ID token and refresh token are each for and who is allowed to inspect each; why the ID token is for the client and the access token is for the API; token validation at the resource server - issuer, audience, expiry, signature, and pinning the algorithm to reject `none` and key confusion; scopes as coarse delegation versus your own fine-grained authorization; and refresh token rotation with reuse detection.

**Fair to look up:** the exact claim names in a less common flow, device flow specifics, the details of token exchange, and the current state of any given spec's draft status.

**The follow-up that catches people:** "the API receives a valid token - what else do you check?" The answer is that a valid token proves who the caller is, not that they may touch *this* object, and conflating the two is the most common serious authorization bug (Q141).

**Depth:** `../11-security` Category 3.

### Q137. "Do you store JWTs in local storage?" `[T]`

The trap is answering yes or no rather than naming the threat model.

> "No, and the reason is XSS - anything in local storage is readable by any script on the page, so one injected script exfiltrates every session. My default is a cookie with `HttpOnly`, `Secure` and `SameSite`, plus CSRF protection, because that combination puts the token out of JavaScript's reach and CSRF is a much better-understood problem than XSS. That said, the deeper answer is that storage is the second question - the first is how long the token is valid and whether it can be revoked, because a stolen fifteen-minute token with rotation is a much smaller incident than a stolen eight-hour one whichever way you stored it. For a pure SPA against a cross-origin API where cookies are awkward, keeping the access token in memory only, with a refresh in an `HttpOnly` cookie, is the version I would defend."

**What scores:** naming the threat, giving a default, and then relocating the question to lifetime and revocation - which is where the real risk reduction is.

### Q138. STRIDE over their system in eight minutes

Do not enumerate all six categories over the whole system - that takes an hour and produces nothing. **Scope it, then run the categories against the boundaries only.**

- **Minute 1-2:** get the data flow diagram down to trust boundaries. What crosses from untrusted to trusted, where does authentication happen, where does data at rest sit, who are the actors including the internal ones.
- **Minute 3-6:** walk each boundary and ask the categories that apply to *that* boundary. At the client-to-API boundary, spoofing and tampering. At the service-to-database boundary, information disclosure and elevation. At any admin path, elevation and repudiation - and admin paths are where the real findings are, because they are built for insiders and reviewed least.
- **Minute 7-8:** rank by **impact times reachability**, and give the top three with a control each. Say explicitly: "these are the three I would fix; the rest I would put in a backlog rather than pretend we can do everything."

**What is being scored:** prioritization, not coverage. A list of thirty threats is a worse answer than three with a control and a reason.

**Depth:** `../11-security` Category 1.

### Q139. Secrets, rotation and KMS: what proves operations

Reading gives you envelope encryption and key policies. Operating gives you these:

- **You have actually rotated something in production**, and you know that the hard part is not generating the new secret, it is the overlap window - both credentials valid simultaneously while every consumer picks up the new one, and the discovery that one consumer caches it at startup and only rotates on a deploy.
- **Key policies are separate from IAM policies**, and a role with `s3:GetObject` and no `kms:Decrypt` produces an error message that wastes an hour.
- **You know what a rotation costs**: re-encryption is not required for envelope encryption because you rotate the key-encrypting key, and knowing that distinction is a good marker.
- **You have a revocation story**, not just a rotation schedule, because the incident case is different from the calendar case (Q114).
- **The honest gap:** somewhere there is a secret that cannot be rotated without downtime. Naming yours is more credible than claiming there is not one.

**Depth:** `../11-security` Categories 8-9.

### Q140. A CVE you have never heard of `[T]`

Say so immediately, then demonstrate the **response process**, which is what the question is actually about.

> "I do not know that one. What I would do with it is the same for any advisory: first, do we use the affected component and on what path - which I can answer from the SBOM rather than by guessing; second, is the vulnerable code path reachable in our usage, because a large share of advisories are not exploitable in a given configuration and the reachability question is what prevents a fire drill; third, severity in *our* context rather than the CVSS base score, because a remote unauthenticated RCE on an internet-facing service and the same CVE in a build-time tool are different problems; then patch, or mitigate if the patch is not available, and document the decision either way."

**The strong addition:** "and I would be more interested in how quickly we could answer the first question - if finding out whether we use a component takes two days, that is the real finding."

**Never** pretend to recognize it. Interviewers occasionally make one up.

### Q141. "How do you handle authorization?" - where the depth is

Not in the model name. The depth is in **where it is enforced and what it is enforced against**.

> "The part that matters is object-level authorization - not 'can this role call this endpoint' but 'may this specific user act on this specific record'. Endpoint-level checks are easy and are almost never the vulnerability; the vulnerability is a handler that loads by id and never checks ownership. So the enforcement has to be at the point of data access, and my preference is to make it structurally impossible to skip - a repository that requires a subject, or a filter applied at the query level - rather than a check a developer has to remember."

Then the model choice as a secondary matter, with the real trade-off: RBAC is legible and gets you a long way and then explodes into role proliferation; ABAC handles the relationship cases at the cost of policies nobody can reason about; and a policy engine centralizes decisions but the enforcement point is still yours. Mention multi-tenancy explicitly - tenant isolation is an authorization property and it deserves a test suite of its own.

**Depth:** `../11-security` Category 4.

### Q142. Supply chain: evidence of practice

Awareness sounds like "we scan dependencies". Practice sounds like:

- **A generated SBOM per build**, stored with the artifact, so the Q140 question takes minutes.
- **Pinned and verified dependencies** - a lockfile that is enforced, an internal proxy or mirror rather than pulling from the public registry at build time, and the knowledge that this also protects against a deleted package and dependency confusion.
- **A build you could describe as trustworthy**: ephemeral runners, no long-lived credentials in CI, provenance attestation on the artifact, and signed images with verification at deploy admission rather than only at push.
- **A policy for what actually blocks a build** - because "fail on any high severity" is how teams end up disabling the scanner. Ours blocks on reachable criticals and files everything else with an SLA.
- **The uncomfortable honest bit:** transitive dependencies are the actual exposure and nobody reviews them; the mitigation is reducing the dependency count and having the SBOM, not pretending to audit them.

**Depth:** `../07-devops` Category 4; `../11-security` Category 10.

### Q143. Discussing a security incident without breaching confidentiality

Abstract the identifiers, keep the mechanism, and **say that you are doing it** - the discipline itself is the signal.

> "I will keep this non-specific about the company and the customer, but the mechanism is the interesting part anyway. The class of issue was *[an object-level authorization gap on an internal admin path]*. It was found by *[a report / a routine review]*. What mattered was the response: we scoped exposure from access logs within a few hours, which was only possible because the logs had the fields we needed - that was luck as much as design. We shipped the fix within *[time]*, and the durable change was *[the query-level enforcement so the class could not recur]*."

**What is scored:** that you did not over-disclose, that you can describe an incident in mechanism terms, and that the lesson was structural. An interviewer who watches you handle confidential material carefully learns something about how you will handle theirs.

**Never** name an unpatched vulnerability in a current employer's system. Some candidates do, and it ends the loop.

### Q144. What is genuinely specific to LLM security

Three things, and be precise, because the domain is full of generic answers:

- **The instruction and data channel are the same.** There is no equivalent of a parameterized query - no way to mark retrieved text as "data, never instructions". So indirect injection through a document, a web page, an email or a ticket is a structural property, not a bug to be patched.
- **The consequence is authorization, not content.** A model reading untrusted content is a nuisance; a model reading untrusted content while holding a tool that can write, send or spend is a confused deputy. The controls are therefore the ones you would use for a deputy: the tool acts with the *user's* privileges, enforced in code outside the model; irreversible actions require confirmation; and the blast radius is bounded by capability rather than by detection.
- **The lethal trifecta** - access to private data, exposure to untrusted content, and an exfiltration channel. Any two are manageable; all three in one context is a data breach waiting for the right document. The architectural response is to break one of the three, most often by separating the trusted-context agent from the untrusted-content one.

Then the model-specific extras: training and inference data handling and retention terms, and the fact that a prompt is not a security boundary no matter how it is worded.

**Depth:** `../11-security` Category 12; `../10-ai-agents` Category 13.

### Q145. "Is our design secure?" with three obvious holes and one subtle one `[T]`

The sequencing is the test, and the instinct to lead with the obvious findings is the trap - it reads as a scanner rather than an architect.

> "Let me separate what I see. Three things I would want changed and would expect you already know about: *[the obvious ones, one clause each, no lecture]*. The one I am more interested in is *[the subtle one]*, because *[the reason it is not visible]* - and I would want to check whether *[the specific test that confirms it]*."

Three properties: you covered the obvious so you are not seen to have missed them, you gave them no more time than they deserve, and you spent your capital on the finding that demonstrates depth. Naming the subtle one as a question rather than an accusation leaves room for the possibility that it is handled somewhere you cannot see.

**Then close with severity, not a list:** "if I could only get one fixed this quarter, it is *[X]*, because *[impact × reachability]*."

### Q146. Secure SDLC for a team with none, deadline unchanged `[A]`

The constraint is the point: you cannot introduce six practices into a team shipping to a date. **Sequence by yield per unit of friction.**

- **Week 1, free and automatic:** secret scanning on the repository and its history, dependency scanning with a policy that blocks only on reachable criticals, and branch protection with review. Nobody has to learn anything and it catches the highest-frequency real issues.
- **Week 2-4, cheap and targeted:** a threat model for the *one* highest-risk component only, timeboxed to ninety minutes with the team in the room. Doing one well teaches the team the method; attempting the whole system teaches them that security is a document.
- **Ongoing, structural:** authentication and authorization moved into shared, hard-to-misuse components, so correctness stops depending on each developer remembering (Q141). This is the highest-value item and the slowest.
- **Later, once there is trust:** a security review gate on defined change types, and a pen test before the release that matters.

**The framing that gets it accepted:** "I am not adding a checklist to your deadline. Everything in the first month is automated and runs without you. The part that needs your time is ninety minutes on the riskiest component, and I will run it."

### Q147. Security investment to a delivery-speed stakeholder `[A]`

Translate into their currency and never use fear as the primary argument - it works once and then it is discounted.

- **Cost of delay versus cost of the incident**, expressed as expected value with an honest range: probability, and the concrete cost - engineering weeks of response, customer notification, the contractual and regulatory exposure, and the deals that stall during due diligence. That last one is often the argument that actually lands, because it is a revenue argument.
- **Reframe as velocity where it is genuinely true.** Automated scanning and shared auth components make delivery *faster* by removing a class of rework and a class of blocked release. Say which items are velocity items and which are pure insurance - conflating them destroys the credibility of both.
- **Ask for a slice, not a program.** "Twenty percent of one engineer for a quarter, and here is what will be true at the end of it" beats a security initiative.
- **Give them the decision, in writing.** "Here is what we are accepting if we do not do this." A stakeholder who declines an explicitly stated risk usually funds the smaller version, and if they do not, the record exists without anyone being blamed.

**The move that works with a hostile version of this stakeholder:** find the item that is both a security win and a delivery win, ship it, and use it as the evidence for the next ask.

---
## 11. Coding and pairing round

### Q148. What a principal-level coding round scores

The problem is easy on purpose. The round is scoring, roughly in order of weight:

1. **Can you still produce working code**, without an IDE doing it for you. This is a floor check, and failing it ends the loop regardless of everything else.
2. **How you work with another engineer**: do you clarify, do you take a hint, do you think out loud, is it pleasant.
3. **Judgement under a time constraint**: what you chose to do first, what you consciously skipped, and whether you said so.
4. **Whether your code would survive review**: naming, boundaries, error handling, testability - at a level proportional to the time you had.

**What it is not scoring:** the optimal algorithm, unless the round is explicitly an algorithms round. Candidates at this level lose here by treating an easy problem as a competitive programming exercise, or by being so senior that they narrate architecture instead of typing.

**The single most useful behaviour:** state your plan in three sentences before typing, and state what you are deliberately not doing.

### Q149. Narrating without slowing down

Narrate **decisions, not keystrokes**. "I am creating a variable called total" is noise; "I am going to keep the counts in a map rather than sorting, because we only need the top one and this stays linear" is signal.

The rhythm that works: talk before each block, then go quiet and type, then talk again. Silence while typing is fine and expected - what interviewers dislike is silence while *thinking*, because they cannot tell whether you are stuck.

Two phrases worth having ready: **"let me think for twenty seconds"** - which buys explicit silence without ambiguity - and **"I am going to do the simple thing here and come back to it if we have time"**, which converts a shortcut into a stated decision.

**When narration genuinely conflicts with progress**, say so: "I am going to go quiet for two minutes and get this working, then walk you through it." Interviewers universally accept this and it is a small positive signal about self-management.

### Q150. The first three minutes, before typing

- **Restate the problem** in one sentence and confirm. Thirty seconds.
- **Ask about the input**: size, whether it fits in memory, sorted or not, duplicates, nulls, whether it streams. One of these usually changes the approach and asking is how you find out.
- **Do one example by hand**, including one edge case. This catches a misunderstanding before it costs twenty minutes and it is where the interviewer will help you if you are about to go wrong.
- **State the approach and its complexity in one sentence**, and offer the alternative you rejected: "hash map, linear time and linear space - the sort is `n log n` and constant space, and I would pick that if memory were the constraint."
- **State the plan for the time:** "I will get a working version, then tests, then handle the edge cases we discussed."

**Do not** spend more than three or four minutes here. The failure mode at senior level is designing for ten minutes and running out of clock with nothing executable.

### Q151. You see the optimal solution immediately `[T]`

Write it - but **do not skip the reasoning**, or the interviewer cannot tell whether you understood it or recognized it.

> "I have seen this shape before, so I will tell you where I am going rather than pretend to derive it. The trick is *[the insight]*, which works because *[why]*. The naive version is *[X]* time; this gets it to *[Y]* by *[the mechanism]*. Let me write it."

Three reasons this is better than silently producing the optimal code: recognizing a memorized solution is worth little and interviewers discount it heavily; stating the insight proves comprehension in ten seconds; and admitting familiarity is honest in a way that reads well.

**The other risk:** writing the clever version and being unable to explain an edge case in it. If the optimal solution is one you half-remember, write the simple one first, get it working, then optimize - a working simple solution beats a broken clever one in every rubric.

### Q152. Tests in a 45-minute round

**Write one test early**, before the implementation is complete - it costs two minutes, it demonstrates the habit, and it gives you a way to run the code. Then finish the implementation, then add the edge cases as tests rather than as print statements.

What to test, in priority order: the happy path, the empty or null input, the boundary (one element, duplicate keys, the exact limit), and the error path if there is one. Four small tests is plenty and each should be one assertion with a name that says what it proves.

**What not to do:** build a test framework, parameterize everything, or write tests for code you have not written yet in a round this short. Also do not say "and of course I would write tests" without writing one - it is the emptiest sentence available in this round.

**If you run out of time:** say what you would test and why, specifically. "I would want a test for the concurrent case, which I have not handled - it would need a latch rather than a sleep" scores far better than silence.

### Q153. What to keep and drop under time pressure

**Keep:** meaningful names, small functions, and a clear boundary between the logic and the IO. These cost nothing and they are what the interviewer is reading for review quality.

**Drop, and say that you are dropping them:** exhaustive input validation, custom exception types, logging, configuration, javadoc, defensive copies everywhere.

The mechanism that makes dropping safe is the sentence: **"in production I would validate here and throw a typed exception; I am going to skip it for time and assume valid input."** Said once, it converts a gap into evidence of judgement. Left unsaid, it is a gap.

**The one thing never to drop:** error handling on the path where failure is *likely and silent* - a parse, a missing key, a division. Silent wrong answers are the worst outcome in a review, and an interviewer will notice that you handled the one that mattered and skipped the ones that did not.

### Q154. Stuck at minute 25 `[T]`

In order:

1. **Say it.** "I am stuck - let me tell you where." Interviewers are usually allowed to help and cannot until you surface it. Hiding it burns the remaining time and scores worse than the stuck-ness itself.
2. **Re-read the problem statement aloud.** A meaningful share of stuck-ness is a misread constraint, and this takes twenty seconds.
3. **Run the smallest failing example by hand** and compare against what your code does. Do not stare at the code; execute it mentally with real values, or add a print and actually run it.
4. **Reduce the problem.** Solve it for one element, or for the unsorted case, or without the constraint that is causing trouble - and say "let me get the restricted version working and then generalize".
5. **Take the hint.** If the interviewer offers one, take it visibly and gracefully: "that helps - so if I *[X]*, then *[Y]* follows." Refusing help is a serious negative; using it well is a positive.

**What not to do:** go silent, start rewriting from scratch at minute 30, or apologize repeatedly. One acknowledgement, then work.

### Q155. The interviewer suggests an approach you think is wrong

Do not argue, and do not silently comply. **Test it cheaply, out loud.**

> "Let me make sure I follow - you are suggesting *[restate it]*. My hesitation is *[the specific concern]*, on this input: *[a concrete example where it fails or costs more]*. Am I missing something, or would you like me to go that way anyway?"

Three outcomes, all fine: they show you why you are wrong and you have learned something in front of them; they realize you are right and you have demonstrated the exact judgement they were testing for; or they say "go that way anyway", in which case you **do it, willingly and without sulking**, which is Q184's disagree-and-commit in miniature.

**The version that loses the round** is either implementing something you think is wrong while making clear you think so, or debating for four minutes of a forty-five minute round. Timebox the disagreement to about a minute.

### Q156. Complexity analysis: when and how precise

**Volunteer it once**, when you state the approach (Q150), and again briefly at the end if the implementation changed it. Do not wait to be asked - being asked means you looked like someone who does not think about it.

Precision needed: the big-O for time and space, and **the variable it is in** - which is the part people get wrong. "Linear" is meaningless if there are two inputs; "linear in the number of events, constant in the number of users, because the map is bounded by the user count which is fixed" is the answer.

The refinements worth having: amortized versus worst case where they differ (hash map resizing, dynamic arrays); the constant factor when it actually matters (two passes over an array beats one pass with a hash map at small n and interviewers like hearing that); and the space cost of the recursion stack, which candidates routinely forget to count.

**If you are unsure:** derive it out loud from the loop structure rather than guessing a symbol.

### Q157. A pairing round on their real codebase

Start by **establishing the map, then the smallest possible loop**, and ask for what you need without apology.

> "Before I change anything: can you show me how you run the tests, and can we run them once so I know they pass? Then - what is this component's job in one sentence, and where does this ticket's behaviour live?"

Then work in visibly small steps: find the existing pattern and follow it rather than importing your own; make one change; run the test; narrate what you expect before you run it. Reading the surrounding code and matching its conventions is a deliberately visible behaviour here, because the round is partly asking "what would this person do to our codebase in week one".

**High-value questions to ask:** "is there an existing helper for this?", "what does this codebase do for *[errors / config / logging]*?", "would your team want this here or in the service layer?"

**Red flags:** rewriting something because you would have done it differently, criticizing the code, or refusing to touch anything without a full understanding of the system.

### Q158. Your solution fails an edge case they supply `[T]`

The recovery sequence, and the calmness matters as much as the fix:

1. **Thank them and reproduce it.** "Good catch - let me add that as a test case first so I know when it is fixed." Turning the counterexample into a test is the single strongest move available here.
2. **Trace it, do not guess.** Walk the failing input through the code out loud until you find the exact line where reality diverges from your model. Guess-and-patch is visible and it is the thing that turns one bug into three.
3. **Say what class of bug it was.** "That is an off-by-one at the boundary - which means I should also check *[the symmetric case]*." Generalizing from the failure is the difference between fixing a bug and reviewing your own work.
4. **Check whether it is a design problem, not a code problem.** Sometimes the right answer is "this input breaks my approach, not my implementation - the fix is *[different structure]*, which would take *[X]*; do you want me to do it or discuss it?"

**Never** be defensive about the case being unrealistic, unless it genuinely is, in which case say so once and handle it anyway.

### Q159. Java choices and what they signal

| Choice | Signals well when | Signals badly when |
| --- | --- | --- |
| Streams | The pipeline is a genuine map-filter-reduce and reads better than the loop | Nested, stateful, or used for side effects; a `forEach` mutating an external list is worse than a loop |
| Plain loops | Early exit, index arithmetic, or the stream version is contorted | Manual iteration over a collection that a one-line stream would express |
| `Optional` | A return type that may legitimately be absent | As a field, a parameter, or wrapped around a collection instead of returning empty |
| Records | Immutable value carriers, especially as intermediate results and DTOs | Used where behaviour belongs with the data |
| `var` | The type is obvious from the right-hand side | It hides the type you need to reason about |
| Exceptions | Fail fast on programming errors; a typed exception for a genuine domain condition | Control flow, or catch-and-log-and-continue, which is the single worst pattern to show a reviewer |
| Mutability | A local accumulator inside a method | Shared mutable state, or exposing an internal collection from a getter |

**The general signal:** immutability by default, small scopes, and no shared mutable state - and the ability to say "I used a loop here because the stream version needed an early exit" when asked. The choice matters less than being able to justify it.

**Depth:** `../01-java` Categories 1 and 5.

### Q160. A take-home instead of a live round

**Scope the time explicitly and in writing.** State the budget you used at the top of the README, and treat the constraint as part of the deliverable: "I spent about three hours; here is what I would do with the next three."

What to include, in order of value per minute: a **README** with how to run it, the decisions you made and the trade-offs; **tests** for the core logic, with a note on what you did not test and why; **a working build** with one command; and code that is boring and readable rather than clever.

What to include that nobody asked for, because it is where you differentiate: a short **"what I would change for production"** section - error handling, observability, the concurrency story, the failure mode - and one **explicitly stated assumption** about the requirements that shows you noticed the ambiguity.

**What sinks take-homes:** over-engineering (a hexagonal architecture with four layers for a CSV parser), no tests, a broken build on a clean machine, or spending twenty hours on a four-hour brief - the last of which reads as poor judgement, not enthusiasm, and disadvantages the candidates who followed the instructions.

### Q161. Build a rate limiter in sixty minutes `[A]`

The round wants a **working implementation plus the distributed conversation**. Sequence it so you have both.

Minutes 0-5: clarify. Per what key - user, IP, API key? What limit and window? Is this one process or a fleet? What happens on exceed - reject with `429` and `Retry-After`, or queue? Is a small overshoot acceptable? The last question is the important one, because it decides everything that follows.

Minutes 5-25: implement **token bucket** in-process, and say why it over the alternatives: fixed window is trivial but allows a double burst across the boundary; sliding log is exact but stores every request; sliding window counter approximates well and is cheap; token bucket handles burst allowance naturally and is a two-field structure - last refill time and current tokens - computed lazily on access rather than with a background thread. Make it thread-safe, and say what you chose - a lock per key or an atomic compare-and-set loop - and why.

Minutes 25-40: tests. Steady rate passes, burst up to capacity passes, burst beyond capacity rejects, refill after waiting, and the concurrent case.

Minutes 40-55: **the distributed version**, which is where the senior signal is. Per-instance limits mean the effective limit is `n × limit` and drifts with autoscaling. Centralized in Redis with an atomic script gives correctness at the cost of a network hop on every request and a hard dependency - so what happens when Redis is down? (Fail open or fail closed is a product decision; say which and why.) The middle ground is a local bucket with a periodically reconciled global allowance, which is approximate and fast.

Minutes 55-60: what you skipped - per-tier limits, the memory bound on the key map and its eviction, the observability you would add (rejection rate per key is the metric that tells you the limit is wrong).

### Q162. Refactoring 200 lines of legacy Java live `[A]`

The order is the answer, and it is deliberately unexciting:

1. **Read and state what it does**, including the behaviour you suspect is accidental. Ask which parts are load-bearing.
2. **Establish a safety net before changing anything.** "Are there tests? If not, I want to write a characterization test that captures the current behaviour - including the behaviour I think is wrong - because otherwise I cannot tell a refactor from a rewrite." This single move is the whole round in many rubrics.
3. **Take the free wins**: dead code, unused parameters, obvious naming, `if` nesting that inverts into guard clauses. No behaviour change, immediately more readable.
4. **Then structural**: extract the pure logic away from the IO so it can be tested; separate the thing that is doing three jobs; replace primitive parameters that always travel together with a value object.
5. **Then the risky ones, and flag them as risky**: changing exception behaviour, changing null handling, changing mutability of something that escapes. Say "this one changes observable behaviour - I would want to check callers before doing it."

**Justify each change in one clause**, and be honest when a change is preference: "this is a readability preference, not a defect - I would raise it as a non-blocking comment" (Q168).

**The trap:** rewriting it in your preferred style. Say explicitly, once, that you are keeping the codebase's conventions even where they are not yours.

---

## 12. Architecture review and code review rounds

### Q163. "What do you think?" about a diagram

Open by **buying context and setting a structure** - never with a critique, and never with praise.

> "Before I react, two questions: what is this optimizing for, and what is the constraint I cannot see - budget, team size, an existing system, a compliance requirement? … Right. Let me go through it in a fixed order so it is easy to follow: first I will trace a request end to end and check I have understood it, then I will look at where the state lives, then failure modes, then the operational and cost picture. Stop me wherever you want to go deeper."

Two things this buys. You avoid criticizing a decision that was forced, which is the fastest way to look junior. And you have announced a method, which is what the round is scoring more than any individual finding (Q90).

**The first substantive thing you say should be a question or an observation, not a verdict.**

### Q164. The order of critique, and why order matters

Order: **purpose → correctness → data → failure → operations → cost → style.**

Correctness first because a design that loses data is not improved by better naming. Data next because where state lives and what is authoritative determines most of the rest. Failure before operations because you cannot discuss runbooks for failures you have not enumerated. Cost late because it is only meaningful once the design is settled. Style last, and briefly, or not at all.

**Why the order changes the impression more than the content:** an interviewer hearing "the naming is inconsistent and also I think this can lose events" concludes that you do not rank. The same two findings in the other order, with the second dropped for time, reads as someone with judgement. Reviewers are evaluated on their prioritization, and the order in which you speak *is* your prioritization, visibly.

### Q165. The design is genuinely good `[T]`

Do not manufacture criticism - that is the trap, and reviewers who invent problems are exhausting to work with. Say so plainly, then be useful in the other four directions:

- **Explain why it is good**, specifically. "The thing I like is that the write path is the only place that touches the ledger, so the invariant is enforced in one place." This proves you understood it, which is a real signal and is what your praise is actually being scored on.
- **Probe the boundaries.** "Where does this stop working? At ten times the volume, what breaks first?" A good design has a known breaking point and the author usually enjoys discussing it.
- **Probe the alternatives.** "What did you consider and reject, and what would have made you choose differently?" This is the most interesting conversation available and it is where you demonstrate range.
- **Probe the un-drawn.** Diagrams omit deploys, migrations, backfills, multi-tenancy, the admin path, and what happens the first time you need to change the schema. There is almost always something real here.
- **Ask what worries them.** They will tell you, and then you are working on the actual problem.

### Q166. Criticizing an architecture whose author is present

Techniques, in rough order of usefulness:

- **Ask, do not assert.** "What happens if the consumer processes this twice?" is the same finding as "this is not idempotent" and lands completely differently.
- **Assume a reason exists.** "Is there something that makes duplicate delivery impossible here that I am not seeing?" Sometimes there is, and you have saved yourself.
- **Attack the design, never the decision-maker,** and never use "you" - "the write path can lose an event", not "you can lose events".
- **Give the cost, not the verdict.** "The consequence would be a double charge at maybe one in ten thousand" tells them how much to care, and lets them own the priority call.
- **Say what you like, and mean it.** Not as a sandwich technique - as accuracy. A reviewer who only finds problems is discounted.
- **Separate blocking from preference explicitly** (Q168).

**What is actually being tested:** whether hiring you means hiring an unpleasant review experience. The findings are almost secondary.

### Q167. Code review: first comments, and deliberate omissions

**First:** correctness and safety. Does it do what the description says, does it break a caller, is there a concurrency or resource issue, is there a security or data-exposure problem, and does the error path lose information or leave a partial state.

**Second:** testability and tests. Is the new logic tested, and is the code shaped so it *can* be tested.

**Third:** clarity where it costs the next reader real time - a misleading name, a function doing three things, an implicit contract.

**Deliberately not commented on:** formatting (a tool's job, and commenting on it signals you have no formatter), preferences dressed as standards, and anything you would only change because you would have written it differently. Also: not the third instance of the same pattern - comment once and say "same applies below", because thirty comments on one theme is a wall, not a review.

**The thing to say out loud in the round:** "I would leave the style points to the linter and spend the review on the two things a tool cannot catch."

### Q168. Blocking versus preference, out loud

Label every comment, explicitly, and the labelling is the skill:

- **"Blocking:"** correctness, security, data loss, a broken contract. State the consequence, not just the rule.
- **"Non-blocking, worth doing:"** a real improvement that does not justify another round trip. Say "take it or leave it and I will approve either way", and mean it.
- **"Question:"** you genuinely do not know, and it may turn out to be fine. Ask more of these than you think you need - a good share of apparent defects are context you lack.
- **"Preference, ignore me:"** used sparingly, and never more than once or twice, because a review full of these is noise.

> "Blocking: if this throws after the first write, we are left with a half-applied change and no way to detect it - that needs to be one transaction or an idempotent retry. Non-blocking: I would pull those three lines into a named method, but not worth another round trip. Question: is the cache invalidation handled somewhere I am not seeing?"

**Why it matters so much at this level:** unlabelled comments make junior engineers treat everything as mandatory, which is how review becomes a bottleneck and how reviewers become feared. Demonstrating the labels is demonstrating that you have run a review culture.

### Q169. Finding a real security flaw in their production design `[T]`

Raise it, immediately, but **calibrate the register**: quietly, factually, as a question, and without an audience reaction.

> "One thing I want to check, and it may well be handled outside this diagram - the admin endpoint here appears to authorize on the role but not on the tenant. If that is the case, an admin from one tenant could read another's records. Is there a filter applied somewhere upstream?"

Then, whatever they answer, **do not perform**. No "this is a serious vulnerability", no visible excitement, no follow-up in front of others. If it is real, say once: "if that is not covered, I would treat it as the top item - happy to talk through it after."

**The judgement being tested** is exactly this: an interview is a low-trust environment with an audience, and how you handle a finding here predicts how you will handle one in their organization. Discretion scores; a flourish does not, even when the finding is correct.

### Q170. What you ask before critiquing anything

Four questions, none taking more than ten seconds to ask:

- **"What is this optimizing for?"** Cost, latency, time to market, team autonomy, compliance. Every critique is relative to this.
- **"What constraints am I not seeing?"** An existing contract, a team that does not exist, a datacentre they cannot leave for eighteen months.
- **"How far along is this?"** A whiteboard sketch invites different feedback from a system in production with customers on it. Critiquing a live system as though it were a proposal is the most common tonal error.
- **"What kind of feedback do you want?"** Sanity check, deep review, or a specific worry. They will often hand you the answer.

**How to ask them without stalling:** ask all four in one breath, in about twenty seconds, and then start. Interviewers read a slow, one-at-a-time interrogation as avoidance; a fast, structured intake reads as professional.

### Q171. Showing mentoring ability in a review round

Mentoring is visible in **how a comment is written**, and you can demonstrate all of it in a single round:

- **Explain the why, once.** "This can deadlock if two threads take the locks in different orders - the general rule is a global lock ordering" teaches; "add a lock ordering here" does not.
- **Link to something,** or offer to. "There is a good writeup on this; I will send it."
- **Ask instead of telling when the author may know something.** It also models that reviewers are not omniscient.
- **Praise something specific,** because juniors calibrate on what is good, and generic praise teaches nothing.
- **Offer the pairing escape hatch.** "This thread is getting long - shall we spend ten minutes on a call?" Knowing when review is the wrong medium is a senior behaviour.
- **Let the small stuff go** when the author is new and the review is already long. Judging the *dose* is the actual skill.

**Say one meta-sentence** in the round so it is not left implicit: "with a newer engineer I would cut this review to the top three items - a review with twenty comments teaches nothing except that review is punishment."

### Q172. Twenty problems, thirty minutes `[T]`

Do not enumerate. **Cluster, rank, and say the strategy out loud** - the selection is what is being scored.

> "There is more here than we can cover, so let me tell you how I am triaging. There are three things I would block on: *[correctness, security, data]*. There is a pattern that shows up about eight times - *[the same unchecked error path]* - which I would raise once as a theme rather than eight times. Everything else is readability, and I would leave most of it. Shall I go deepest on the blocking three?"

**The three principles:** blockers first; themes instead of instances; and an explicit decision to leave things unsaid. Naming the count ("about eight instances") proves you saw them all without spending the time.

**The failure mode:** working top to bottom through the file, spending the round on the first sixty lines, and never reaching the real defect on line 180.

### Q173. What a principal reviewer notices that a senior does not

- **The absence of things.** No idempotency on a retried path, no bound on a queue or a collection, no timeout on a call, no cleanup path, no way to tell it failed. Senior reviewers review the code that is there; the expensive defects are usually omissions.
- **The blast radius of a change**, not just its correctness: who else calls this, what happens during the deploy when both versions are live (Q110), what this does to a caller's error handling.
- **Coupling created quietly** - a shared table, a field another team now depends on, an enum that has just become a public contract.
- **Cost and scale implications of an innocuous line:** an N+1 in a loop, a query without a limit, a log line at debug level in a hot path, a new metric label with unbounded cardinality (Q57).
- **The organizational read:** this is the third team to build this; this pattern is about to be copied twenty times; this is a workaround for a platform gap and the platform gap is the real ticket.
- **What is not worth saying.** Restraint is the marker that is hardest to fake.

### Q174. Reviewing an event-driven design with a hidden ordering assumption `[A]`

Run it as the conversation, not as a list of findings.

**Establish first** (Q170): what is the event, who produces it, who consumes it, and what does each consumer do that is not idempotent?

**Then probe the ordering assumption specifically**, and do it with a scenario rather than a principle: "Let me walk one case. `AddressChanged` and then `OrderShipped` are published a few milliseconds apart. If they are on different partitions - or the same partition but the consumer is running with concurrency greater than one, or one is retried after a transient failure - can the shipping consumer see them out of order? And if it does, what does it do?" A concrete two-event trace is far more effective than saying "this assumes ordering".

**Then the standard follow-ups** that determine whether the assumption is fatal: what is the partition key, and does it match the entity whose order matters; is the consumer concurrent within a partition; does the retry path preserve order or move a message to the back; and what happens on a rebalance or a replay from the dead-letter queue.

**Then the fixes, ranked with their costs:** partition by the entity id so ordering is preserved where it matters (cheap, limits parallelism per key); make consumers order-independent using a version or sequence number on the entity and dropping stale updates (the most durable answer, needs a version everywhere); a per-entity sequencer or an idempotent state machine (correct, most work); or accept it and reconcile (sometimes genuinely right, and saying so is a mark of judgement).

**The closing move:** "the deeper issue is that the ordering assumption is not written down anywhere. Even after we fix this instance, I would want it stated in the event contract, because the next consumer will not know."

### Q175. Writing a code review standard live `[A]`

The instinct is to write rules. The strong answer writes **outcomes, defaults and a small number of rules that are enforced by machines.**

- **State the purpose in one sentence,** because every disagreement gets resolved against it: *"review exists to catch defects a tool cannot, to spread context, and to keep the codebase legible - not to enforce taste."*
- **Automate everything automatable, and say so:** formatting, imports, linting, coverage thresholds, dependency and secret scanning. A rule a human enforces is a rule that generates conflict.
- **Define what blocks.** Correctness, security, data loss, a broken public contract, missing tests on new logic. Everything else is non-blocking by default, with the labelling convention from Q168 written into the standard.
- **Set service levels in both directions:** first response within one working day; pull requests under a size threshold, because review quality collapses past a few hundred lines and that is the highest-leverage rule in the whole document; authors respond to every comment even if only to decline.
- **Define escalation.** Two round trips of disagreement means a call, not a third round trip. Unresolved after that, a named person decides. Without this, review disputes become political.
- **Cover the exceptions honestly:** hotfixes reviewed after the fact but always reviewed; a single approval is enough, and requiring two just slows everyone down unless the code is genuinely high-risk, in which case name those paths.

**Close with adoption, because that is the real question:** "I would introduce this as a default that teams can override with a documented reason, and I would measure review latency and pull request size rather than compliance - if those two move, it is working."

---

## 13. Behavioural and leadership under pressure

> Q186-Q191 have no scripted answer. They must be your stories - Part C of [scenario-questions.md](scenario-questions.md) says how to build and rehearse them.

### Q176. STAR-L time budget

For a two-and-a-half minute answer, roughly: **Situation 20 seconds, Task 15, Action 80, Result 25, Learning 15.**

- **Situation** is context only - the system, the scale, the stakes, in two sentences. Interviewers do not need the org chart.
- **Task** is *your* specific responsibility, and the word "I" belongs here. This is where candidates accidentally describe the team's task.
- **Action** is the bulk, and it should contain at least one decision with an alternative you rejected. Actions without a decision are a description of a job.
- **Result** must have a number or a concrete state change, and should include the second-order effect (Q5).
- **Learning** is what separates you from a mid-level candidate: what you would do differently, or what rule you now apply.

**The letter candidates overrun is Situation** - typically a minute of background before anything happens. Practice the two-sentence version specifically; it is the single highest-yield behavioural drill.

### Q177. Quantifying when the numbers are confidential or gone

Never invent a number. Four legitimate substitutes:

- **Ratios and multiples** instead of absolutes: "we cut the deploy time by about two thirds", "it was roughly a tenth of the previous cost".
- **Orders of magnitude with a hedge:** "on the order of ten thousand requests a second at peak - I am giving you the magnitude rather than the figure."
- **Time and people:** "it took four engineers about six weeks", "it removed roughly a day a week of manual work from the on-call rotation". These are rarely confidential and are perfectly concrete.
- **The state change:** "before, a release needed a two-hour window and a rollback plan approved by three people; after, it was a button and we did it during the day." No number, entirely quantified in effect.

**Say the constraint once, plainly:** "I cannot give exact figures for that customer, so I will give you the shape." Handled well, this is a small positive signal (Q143).

### Q178. "Tell me about a failure" - the right amount `[T]`

The right amount is: **a real failure, with real consequences, that you owned and learned from, and that is not disqualifying for this job.**

**Too little** is the more common error and the more damaging one. "I once underestimated a timeline" reads as either no self-awareness or an unwillingness to be candid, and interviewers write down "no genuine failure offered". At nineteen years the claim is implausible on its face.

**Too much** is a failure that reveals a pattern the role cannot tolerate - a security incident caused by carelessness for a security-adjacent role, or a failure you clearly still blame someone else for.

The calibrated shape: a decision that was **defensible at the time and wrong in hindsight**, with the cost stated plainly, a clear statement of what you owned, and a specific change in how you now work - which you can point to being applied since.

**The give-away of a rehearsed non-answer:** a failure that is secretly a strength. Interviewers have heard "I care too much about quality" and it is scored as evasion.

### Q179. Conflict with a colleague, credibly

Credible answers have these properties, and sanitized ones lack them:

- **The other person's position is stated fairly, and had merit.** If your account makes them obviously wrong, the interviewer concludes you cannot represent a disagreement accurately - which is the actual skill being tested.
- **There was a real cost** - a delay, a rewrite, a tense meeting. Conflicts with no cost were not conflicts.
- **You changed something** - your position, your approach, or how you were communicating. "I explained it again more clearly and they came around" is not a conflict story; it is a story about being right.
- **The resolution mechanism is named:** data you both agreed to gather, a timeboxed spike, a prototype, an escalation you both agreed to, a decision record.
- **The relationship afterwards is addressed.** This is the part most candidates omit and it is what a manager is actually listening for.

> "We disagreed for three weeks and it was slowing the team. What broke it was agreeing on the test rather than arguing the conclusion - we spent a week measuring, the numbers went his way on the main case and mine on the tail, and we split the design. We worked together fine afterwards; if I had that time again I would have proposed the measurement in week one instead of week three."

### Q180. Influence without authority: what counts

Weak evidence: "I persuaded them", "I explained the benefits", "I built consensus". Unfalsifiable and universally claimed.

Strong evidence, roughly in ascending order:

- **You built the thing that made the right way easier than the wrong way,** and adoption followed without a mandate. A template, a library, a pipeline, a dashboard that made a problem visible.
- **You changed a decision you did not own**, and you can name who made it and what changed their mind - usually data, a prototype, or a small pilot rather than an argument.
- **You gave away credit** to get something adopted, and it stuck.
- **It persisted after you stopped pushing.** This is the strongest evidence of all, and the sentence to end on: "that standard is still in use and I have not touched it in two years."
- **You lost one and it was still fine** - you can name a case where the org went the other way and you supported it (Q184).

**The pattern:** influence at principal level is demonstrated by artifacts and durability, not by persuasion anecdotes.

### Q181. Team success, your contribution unmistakable

Use **"we" for the outcome and "I" for the decisions**, and be specific about the decisions rather than claiming a share of the result.

> "The team delivered it - about eight people over four months. The parts that were mine: I made the call to keep the old path running in parallel for six weeks instead of cutting over, which cost us a sprint and meant the rollback was a config change when we found the data problem in week five. I owned the interface between the two teams and wrote the contract tests that made the integration boring. And I was wrong about *[X]* - *[colleague's role]* pushed back and they were right."

Three mechanisms at work: the decisions are specific and attributable to you; crediting others makes the whole account more believable, not less; and admitting one thing you got wrong is what makes the claims about what you got right land.

**The failure modes are symmetrical.** Pure "we" leaves the interviewer with no evidence about *you* - the single most common behavioural failure for collaborative senior candidates. Pure "I" on a team effort reads as someone who will be a problem.

### Q182. A second example of the same competency `[T]`

Almost always one of three things: the first example did not clearly demonstrate the competency; they suspect it was a one-off or that the competency belongs to someone else in the story; or the rubric requires two data points and they are being thorough.

**What to do:** give a genuinely different second example - different company, different scale, different mechanism - and make the *competency* the visible thread rather than the domain. If the first was mentoring one engineer at Sonata, the second should be something like changing how a team hired or onboarded at Verizon.

**A weak second example costs you more than having no second example**, because it converts "probably has this" into "the first one was the only one". So if you genuinely have only one, say so honestly and go deeper on it: "I have one strong example of that and a partial one - would you rather I go deeper on the first or give you the partial?"

**Preparation implication:** your story bank needs **two** examples for the three or four competencies most central to the role, not one each for ten (Q185).

### Q183. A behavioural question about a situation you have never been in

Do not fabricate, and do not just say no. Three legitimate moves, in order of preference:

- **Offer the nearest true analogue and label it as such.** "I have not managed someone out, but I have had to tell a contractor their work was not at the level we needed and manage that to a conclusion - can I use that?" Interviewers nearly always accept.
- **Answer the underlying competency directly** if no analogue exists: "I have not been in that exact situation. What I think it requires is *[X]*, and here is how I have handled the adjacent version of it."
- **Say how you would approach it, flagged clearly as hypothetical**, and make it concrete rather than platitudinous. This is the weakest of the three but it is far better than a vague story that turns out on questioning not to be what was asked.

**Never** stretch a story to fit. The follow-up questions will expose the stretch and the cost is not the missing example, it is the credibility of everything else you said.

### Q184. Disagree and commit, both halves

Most candidates tell the first half and stop, which reads as "I disagreed and was proved right" - the opposite of what the question is for.

The structure that shows both:

- **The disagreement was real and well-argued.** State your position and the strongest version of theirs.
- **The decision went the other way, and the mechanism was legitimate** - it was their call, or the data was ambiguous and someone had to decide.
- **You committed visibly.** This is the load-bearing part, and it needs evidence: you presented the decision to your team as the decision, without distancing yourself; you did the work well; you did not relitigate it in the corridor.
- **You set the condition for revisiting it** - not as a threat, as engineering. "We agreed to look again if the error rate went above *[X]*."
- **What actually happened, honestly.** It is a stronger story if you turned out to be wrong. If you turned out to be right, the emphasis must be on how it was revisited, not on being right.

> "I lost that one. What I did not do was let the team think I was carrying someone else's decision - I presented it as ours and built it properly. Six months later the constraint I had worried about did show up, and because we had agreed the threshold in advance, revisiting it was a five-minute conversation instead of an argument."

### Q185. A story bank without ten memorized scripts

Build **five or six deep stories, each with four or five faces**, rather than ten shallow ones. The same project can answer questions about architecture, conflict, failure, influence and mentoring - what changes is which part you foreground (Q104).

The practical construction:

- **Write each story once as a full account** with the real details, then write a **two-sentence spine** for it: system, stakes, your decision, outcome, learning. The spine is what you memorize; the details you know because you lived them.
- **Tag each story with the competencies it can serve**, and check the grid for gaps. Common gaps for a technical candidate: hiring, managing poor performance, and a stakeholder conflict outside engineering.
- **Rehearse the compression, not the words.** Practice each story at two minutes and at six, because interviewers ask for both and the six-minute version is not the two-minute one spoken slowly.
- **Keep the numbers on one page** and re-read it the morning of the loop. Numbers are the first thing to evaporate under pressure and the first thing an interviewer writes down.

**Why memorized scripts fail:** they are audible, they do not survive a follow-up that goes sideways, and they collapse when the question is phrased unexpectedly. A spine plus real memory survives all three.

---

## 14. Bar raiser, curveballs and recovery

### Q192. What a bar raiser optimizes for

Not depth - other rounds cover that. A bar raiser is asking: **would this candidate raise the average of the people already here, and is there anything in this loop that we would regret?**

That produces a specific behaviour set: they ask across topics rather than deep in one; they probe inconsistencies between rounds; they push until you reach the edge of what you know, deliberately, because the edge is where the calibration is; and they weight self-awareness, disagreement handling and how you respond to being wrong far more heavily than any technical answer.

**Two practical consequences.** First, **being taken to the edge is the design of the round, not a failure** - the score is on how you behave there (Q195). Second, consistency across the day matters: a story that grows between round two and round five is the kind of thing this round exists to catch.

### Q193. You realize you gave a wrong answer twenty minutes ago

**Correct it, immediately, briefly, and then move on.** This is one of the few situations in an interview where the recovery scores higher than never having erred.

> "Before we go on - I want to correct something I said earlier. I told you *[X]*; that is not right, it is *[Y]*, and the reason I got it wrong is *[the actual reason]*. It does not change the conclusion I drew, but I did not want to leave it standing."

Why it scores: self-correction is the single clearest evidence that you monitor your own accuracy, which is what a panel is really trying to establish about a person they will trust with technical decisions. Interviewers write this down.

**The two ways to get it wrong:** apologizing at length, which makes a small thing large; and correcting it so obliquely that they cannot tell you have retracted anything. One clean sentence, then continue.

**If you realize after the interview**, put it in the follow-up note (Q213) - one sentence, no drama. It works.

### Q194. "I do not think that is right" - and they are wrong `[T]`

Play it in this order:

1. **Assume you might be wrong first, genuinely.** "Let me check my understanding" costs nothing and occasionally saves you.
2. **State the mechanism, not the conclusion.** Mechanism is checkable; a conclusion is a contest. "My understanding is that the proxy is bypassed on self-invocation, because the call does not go through the proxy object at all - is there a configuration where that is not the case?"
3. **Offer them a world where they are right.** Different version, different context, different definition of a term. Very often that is the actual explanation.
4. **If they hold and it is not material, concede the floor without conceding the fact.** "I may well be misremembering - I would want to check it." Then move on. You have not agreed you are wrong; you have declined to fight.
5. **If it is material to the design under discussion,** say so once and proceed conditionally: "if it does work the way you describe, then my concern goes away - I will design assuming it does not, and we can check."

**What is scored:** the calibration and the temperature, not the fact. Many interviewers do this deliberately, and the two failing responses are instant capitulation (suggesting you have no conviction) and winning the argument at length (suggesting you will be hard to work with).

### Q195. "I do not know", so that it adds evidence

The three-part form: **the boundary, what you do know, and how you would find out.**

> "I do not know how *[X]* handles that - I have not used it. What I know about that class of system is *[the principle]*, so my expectation would be *[Y]*. The way I would settle it is *[a specific, cheap experiment or source]*, and I would want to before designing around it."

Then, crucially, **stop**. Do not fill the silence with a guess. The most damaging pattern is a confident-sounding non-answer, because the interviewer now has to discount everything else you said.

**When you should guess, and how:** if they ask you to reason about it, label the confidence explicitly - "I am reasoning from first principles here rather than experience, so treat this as a hypothesis". That is welcomed; unlabelled speculation is not.

**One "I do not know" per round is a positive signal.** Four is a level problem, so know which topics you are willing to reach the edge on.

### Q196. A silent interviewer with no signal

Assume nothing from the silence - some interviewers are trained to give nothing, and reading it as disapproval will degrade your performance in a self-fulfilling way.

**Create your own signal** by making the round require input:

- **Checkpoint explicitly.** "That is the write path - shall I keep going or is there somewhere you would rather I spend the time?" A silent interviewer will still answer a direct question.
- **Offer a fork.** "I can go deeper on the consistency model or move to failure modes - which is more useful?"
- **Ask for calibration once, plainly.** "Is the level of detail right for you?"
- **Timebox yourself out loud**, since you have no feedback to correct against: "I will give this three minutes and move on."

**Manage your own state.** Do not speed up, do not add filler, do not start explaining more simply on the assumption they are lost. Keep the structure you planned and let the checkpoints do the work.

### Q197. A hostile or distracted interviewer `[T]`

**In your control:** your structure, your tone, the quality of what you say, and whether you keep checkpointing. Nothing else - and specifically, not their engagement.

Concrete tactics: for **distraction**, shorten your answers and ask more questions, because a distracted person re-engages when asked something directly, and get the key claim into the first sentence of each answer in case that is all they hear. For **hostility**, do not match it and do not become deferential; stay flat and factual, and treat aggressive challenges as technical questions - answer the content and ignore the tone. If they interrupt, let them; finish their point, then say "coming back to your earlier question".

**Do not** try to win them over with more enthusiasm - it reads as anxious and makes it worse.

**Afterwards:** it is legitimate to mention it to the recruiter, once, factually and without complaint, and only if it was extreme. And remember that a hostile round is sometimes deliberate stress testing - in which case the flat, unbothered response is exactly the pass condition.

### Q198. "How many ATMs are there in India?"

Asked at principal level because it is a **pure test of estimation method with no domain knowledge to hide behind** - the same skill as sizing a system (Q62).

Run it in four visible steps: **choose a decomposition and say why** (population and banking penetration, or a per-bank count - pick one and name the alternative); **assign numbers with the reasoning attached** ("1.4 billion people, maybe half with a bank account, and an ATM might serve a few thousand account holders in an urban area and far fewer in rural"); **do the arithmetic out loud, keeping one significant figure**; **sanity check against something you know** ("that gives me a few hundred thousand - as a cross-check, a large bank probably operates tens of thousands, and there are a handful of very large banks, so the magnitude holds").

Then the closing move that scores: **name which assumption dominates the error.** "The answer is most sensitive to accounts per machine - if that is off by a factor of three, so is my answer. If this mattered, that is the one number I would go and look up."

**What loses:** guessing a number, apologizing for not knowing, or refusing to engage.

### Q199. "What would you do differently in the last five years?"

It is a self-awareness and ambition question wearing a regret costume. They are checking whether you evaluate your own trajectory, and whether the answer is consistent with why you are in the room.

The shape that works: **one specific, non-trivial regret, what it cost, and the change you already made.**

> "I stayed in a comfortable scope too long - I was doing good work at Verizon in year nine and could have pushed for a wider remit two or three years before I did. The cost was that I learned the organizational side of architecture later than I should have. The change is visible in how I have worked since 2022: I have gone after the cross-team problems deliberately rather than waiting to be handed them, which is exactly why I am looking at a role like this one."

**Avoid:** a technology regret ("I wish I had learned Kubernetes sooner") which is small and dodges the question; and anything that reads as regret about the industry or your employers rather than about your own choices.

### Q200. "Why you over ten years of pure Java?" `[T]`

Do not disparage the alternative and do not concede the frame. **Reframe onto what the role actually needs, then be specific about the differential.**

> "If the job is to be the deepest Java specialist in the building, that person might be the better hire and I would say so. What I would bring that is harder to find is *[the specific combination]*: I have built the same architecture twice in two ecosystems, so I can tell a framework accident from a real constraint; I have carried systems at telecom scale through incidents and migrations, not just built them; and I have taken AI features to production with the evaluation and cost discipline of a systems engineer, which is currently rare. For a principal role, my read is that the scarce skill is judgement across those boundaries rather than one more level of depth in one of them - but you know the shape of the problem better than I do, so is depth genuinely the constraint here?"

**The two failure modes:** defensiveness ("I have plenty of Java experience"), and dismissing the specialist. Ending with a question turns a challenge into a conversation and often gets you real information about what they are worried about.

### Q201. Rapid-fire: twenty questions in twenty minutes

The strategy inverts. **Optimize for coverage and precision, not depth.**

- **Answer in one or two sentences, then stop.** Silence is the signal that you are done. Candidates who give three-minute answers get through six questions and are scored as unable to read a room.
- **Lead with the answer**, then one clause of justification. "Read committed, because the anomalies I actually get bitten by are lost updates, and I handle those with an atomic write rather than raising isolation."
- **Say "I do not know" fast** and move on (Q195). In this format, hesitation is more expensive than the gap.
- **Offer depth rather than taking it.** "Happy to go deeper on that if useful" gives them the choice and takes two seconds.
- **Ask about the format up front** if it is unclear: "would you like short answers so we can cover more ground?" That one question demonstrates the awareness the round is testing.

**What is being scored:** breadth, calibration, and whether you can be concise - which is often a proxy for how you will behave in meetings.

### Q202. A question spanning three packs

Pick the thread by **what the question is actually deciding**, name the other two, and offer them.

> "That touches three things - the retrieval quality, the authorization boundary, and the cost profile. I think the one that decides the design is the authorization boundary, because it constrains the other two, so let me start there and come back to the others. Stop me if you would rather start somewhere else."

Three properties: you demonstrated the breadth in one sentence without spending time on it; you took a position on what matters, which is the actual signal; and you handed them the fork (Q65).

**The two failure modes:** answering only one thread as if the others do not exist, which reads as not seeing the interaction; and trying to cover all three in parallel, which produces four minutes of shallow material with no conclusion.

**A useful habit:** when you finish the chosen thread, close the loop - "that is the authorization piece; the cost consequence of it is *[one sentence]*, and I have not touched retrieval." Now the breadth is in their notes too.

### Q203. Four minutes into a 90-second question `[T]`

Land it, do not abandon it - a mid-sentence stop is jarring and loses the content.

> "I am going long on this - let me land it in two sentences. The core of it is *[the one-sentence answer]*, and the practical consequence is *[the decision it drives]*. Happy to go back into the detail if it is useful."

Then **actually stop**, and let them redirect.

**Why the meta-comment helps rather than draws attention to the problem:** it demonstrates real-time self-monitoring, which is a genuine signal, and it hands back control. Interviewers rarely penalize a candidate who notices; they penalize the one who does not.

**The prevention** is structural: state the shape before you start ("three things, about thirty seconds each"), because a stated structure makes overrun audible to you as it happens. And watch for the trigger - overrun almost always happens on your favourite topic, so know which one that is and set a hard limit on it in advance.

### Q204. Energy across a five-round day

What degrades, in this order: **the structure of your answers** (you stop scoping and start free-associating), **your listening** (you answer the question you expected), **your numbers** (they evaporate first), and **your warmth** (which the last interviewer of the day is the only one to see, and they are often the bar raiser).

Countermeasures that actually work:

- **Eat and drink between rounds, every time**, and get out of the chair for two minutes. This is the single largest effect.
- **Reset with a fixed ritual** at the start of each round - the same opening question to the interviewer (Q2) gives you thirty seconds to breathe and re-anchors your structure.
- **Keep one index card of numbers** visible for remote loops, and re-read it between rounds. Not a script; six numbers.
- **Do not carry the last round with you.** Write one line about it, close it, and start clean. Ruminating on a bad round is what turns one bad round into three.
- **Front-load nothing in preparation on the day.** Cramming in the morning degrades the afternoon; a short re-read of your own cheatsheet is the whole budget.

**Ask for the schedule in advance** and, if you get a choice, put the round you care most about early.

### Q205. Design your own bar raiser round `[A]`

Six questions, forty-five minutes, and every one has a stated purpose - which is what the exercise is scoring.

- **"Tell me about a decision you made that you now think was wrong."** (5 min) Purpose: self-evaluation without prompting. A candidate with no answer at this level has either not decided anything or does not review.
- **"Take something you built and tell me how you would attack it."** (8 min) Purpose: can they hold their own work at arm's length (Q206)? Strongest single question in the set.
- **"Here is a design with a subtle flaw - walk me through it."** (10 min) Purpose: depth *and* how they deliver a finding (Q166). Two signals from one question.
- **"What is something your last team did badly that you failed to change?"** (7 min) Purpose: accountability without blame, and evidence of real organizational effort rather than complaint.
- **"Teach me something in your domain I probably do not know."** (8 min) Purpose: genuine depth, and whether they can pitch to an audience - it is very hard to fake and very hard to prepare for.
- **"What would make you leave a job in the first year?"** (5 min) Purpose: the regret risk, honestly surfaced.

**The meta-point to state:** none of these has a right answer, so the rubric has to be behavioural - specificity, ownership, whether they went to the edge, and whether they were pleasant while being pushed. And I would deliberately include **one question I expect them to fail**, because how they handle the edge is the whole purpose of the round (Q192).

### Q206. Attack your own strongest project `[A]`

The scoring is on whether you can produce a critique **as sharp as a hostile outsider's**. A soft self-critique is worse than none, because it demonstrates the blind spot directly.

Structure it as a real review (Q164), of your own thing:

- **The decision I would reverse.** Not a small regret - a real one, with the cost. "We built the aggregation in the application because the database team had a six-week queue. It worked, and it cost us a class of consistency bug for two years."
- **The thing that only works because of an accident.** Every system has one - a volume that never materialized, a customer who never used the feature, a limit nobody hit. Name yours.
- **What it cannot do.** The requirement that would force a redesign, and how far away it is.
- **The operational debt.** What would happen if the two people who understand it left; what is not documented; what has never been tested, including the failover.
- **The cost nobody looks at**, and what it would be at three times the volume.
- **What I would build instead today**, and honestly whether the difference is a genuine improvement or just current fashion.

**The closing sentence that separates this from performative humility:** "the one I actually still worry about is *[X]*, and the reason it is not fixed is *[the real reason - priority, politics, or that I was wrong about its importance]*."

---

## 15. Reverse interview, debrief signals, offer and negotiation

### Q207. "Do you have questions for us?"

**Two to four per round, and different ones per interviewer.** Ten is an interrogation; zero is disqualifying at principal level, because it reads as not evaluating them.

What they signal:

| Question type | Signals |
| --- | --- |
| About the work itself and its hardest part | Engagement with the actual role |
| About what has been tried and failed | Seniority - you know context beats ideas |
| About decision rights and scope | That you are evaluating the level (Q209) |
| About what would make this role a failure | Confidence and realism |
| Only about process, benefits and remote policy | Not evaluating the work - save these for the recruiter |

**Have them per interviewer**: an engineer gets the on-the-ground question (Q211), the manager gets scope and expectations, the skip-level or executive gets strategy and the eighteen-month picture.

**The one to always keep in reserve:** "what is the thing about working here that you would want to know if you were me, that does not come up in interviews?" It is disarming, and the answers are unusually honest.

### Q208. Five questions that reconsider your level upward

Each of these makes the interviewer picture you operating at the higher level while they answer:

- **"What is the decision this team keeps re-making, and why does it not stay decided?"** Signals that you think in terms of durable decisions and organizational memory.
- **"Where does the architecture disagree with itself today?"** Presupposes that a real system has contradictions and that noticing them is your job. Very few candidates ask anything like this.
- **"Which of your current constraints are real, and which are just old decisions nobody has revisited?"** Signals that you distinguish the two, which is most of what a principal does.
- **"If I did this job perfectly for eighteen months, what would be different that is not on anyone's roadmap?"** Moves the conversation to second-order impact (Q5) and often gets a genuinely revealing answer.
- **"What is the strongest argument against the direction you have chosen, and who is making it?"** Signals comfort with dissent and interest in the real politics.

**Delivery matters as much as content.** Asked with curiosity, these read as principal; asked with an edge, they read as auditing the interviewer. One or two per round, not five.

### Q209. Is the scope real?

Ask about **artifacts and history**, because both are checkable and neither can be answered with an aspiration:

- "Can you give me an example from the last two quarters where someone at this level changed the direction of something? What did they do specifically?"
- "What would this person decide alone, what would they recommend, and what would they be told?" (Q26)
- "Who else is at this level, and what do they spend their time on?" The single most informative question - if the answer is "they run projects", the role is a delivery role.
- "When this role and a delivery deadline conflict, how has that gone before?"
- "What is the budget or the headcount or the platform this role influences, if any?"

**Reading the answers:** concrete examples with names and outcomes mean the scope is real. Descriptions of responsibilities rather than events mean the role is aspirational - which can still be a good job, but you are being hired to *create* the scope, and that is a different decision and a different negotiation.

### Q210. Your questions reveal a dysfunctional organization `[T]`

**Usually yes, continue - but change what you are doing in the loop.** Withdrawing on partial evidence from two conversations is expensive and often wrong; interviewers describe their own organization badly, and one bad answer is not a pattern.

What to change: switch from selling to **diagnosing**. Ask the same question of three different people and compare - the variance is more informative than any single answer. Ask about the specific dysfunction directly and neutrally: "you have mentioned re-orgs twice - how has that affected long-running technical work?" Ask an engineer, not a manager (Q211).

**When to actually withdraw mid-loop:** consistent evidence of something you will not tolerate - people spoken about with contempt, an obviously broken on-call culture presented as normal, or dishonesty about the role. Then withdraw politely and briefly, without a critique.

**The other reason to continue:** an offer is optionality and information, and dysfunction plus a real mandate to fix it is a legitimate principal job - as long as you are choosing it with your eyes open rather than discovering it in month two.

### Q211. What to ask an engineer but never the manager

- **"What is the last thing that got shipped late, and what actually caused it?"** Managers give you the sanitized version; engineers give you the mechanism.
- **"What is on-call actually like? How many times were you woken up last month?"** A number, from someone who was there.
- **"What is the codebase like to work in on a Tuesday afternoon?"** The honest answer to this is worth more than any architecture diagram.
- **"How long from your first day to your first production deploy?"** A concrete proxy for tooling, onboarding and trust.
- **"What do people complain about that leadership does not know about?"**
- **"Who would you go to if you were stuck at 11pm, and would they mind?"**

**How to ask them:** signal that you want the real answer and that you are not going to quote them. "I am asking you rather than your manager because I want the version that does not get presented upward - what is it actually like?" Most engineers respond well to being treated as the credible source.

### Q212. Reading the loop itself

The process is a genuine information channel about how the organization operates:

| What you observe | Reasonable inference |
| --- | --- |
| Interviewers arrive on time, having read your resume, with prepared questions | They take hiring seriously, which usually correlates with taking engineering seriously |
| Repeated questions across rounds, no coordination | No structured loop; the debrief will also be unstructured |
| Nobody can describe the role's first project | The role is not funded by a real problem yet (Q209) |
| Scheduling drags for weeks between rounds | Either low priority, or an organization that cannot make decisions - both matter |
| They ask nothing about how you work with people | They will not evaluate that in your colleagues either |
| An interviewer is visibly relieved to discuss a problem with you | Real pain, and real scope for you |
| Everyone describes the same technical problem | It is genuinely the priority - prepare for it in the offer conversation |

**Positive signals worth noticing:** being asked what you would want to work on, being introduced to people not on the panel, and questions about your start date and constraints late in the loop.

### Q213. The follow-up note

Worth sending, to the recruiter or the hiring manager - short, once, within a day. It is not a deciding factor, but it is cheap and occasionally consequential.

What belongs in it: one sentence of thanks; **one specific thing from the conversation** that shows you were listening and thinking afterwards; a correction if you got something wrong (Q193), stated in one sentence and no more; and a plain statement of interest and any relevant logistics.

> "Thanks for the time today. The question about how the batch and the streaming path stay consistent stuck with me - I have been thinking about it since and I would approach it with *[one sentence]*. One correction: I said *[X]* about the retry semantics and that was not right; it is *[Y]*. I am genuinely interested in the role, and I am available for anything further next week."

**What does not belong:** a summary of your qualifications, a long essay, individual notes to five interviewers (they compare them), or anything that reads as chasing.

### Q214. Compensation expectation with no signal `[T]`

Try once to get their range first - it is a reasonable ask and often works:

> "I would rather not anchor either of us before I understand the scope. Do you have a band for this level? If you tell me the range, I can tell you immediately whether we are in the same territory and we save both of us the trouble."

If they insist, **give a range whose bottom you would genuinely accept**, tied to the role rather than to your history, and keep it open:

> "Based on the scope we have discussed and what I have seen for principal roles in this market, I am looking in the region of *[X to Y]* total. That is not a firm position before I understand the whole package - if the role is bigger than I currently think, my number moves with it."

**The two mistakes:** a single number, which becomes the ceiling instantly; and refusing repeatedly, which turns a pleasant conversation adversarial over something you will have to answer eventually. Never give a number below what you would accept in the hope of seeming reasonable - it will be the offer.

### Q215. Levers besides base salary

| Lever | Typically movable | Notes |
| --- | --- | --- |
| **Level or title** | Sometimes, and it is the most valuable | Moves the whole band and every future raise. Ask early, not at offer stage |
| Sign-on bonus | Usually the most movable | Comes from a different budget and does not disturb internal parity - the first thing to ask for |
| Equity or long-term incentive | Often, more than base | Ask about the vesting schedule and refresh policy, not just the grant |
| Base | Least movable at a large company | Bands are real; at a startup it is more open |
| Start date | Almost always | Genuinely valuable if you need a break between roles |
| Remote or travel arrangements | Often, and often undervalued | Get it in writing, not as an understanding with one manager |
| Scope commitments in writing | Sometimes, and rarely asked for | The one that matters most at principal level - the first project, the decision rights, the review timeline |
| An early review | Frequently | Useful when they cannot move now: a six-month review with defined criteria |

**The one to prioritize** at principal level is the level itself, then scope in writing. A larger sign-on into a role with no mandate is the expensive mistake.

**How to ask:** one consolidated, prioritized ask rather than serial requests. "If you can do *[A]* and *[B]*, I will accept today" is far more effective, and far less irritating, than three separate rounds.

### Q216. A competing offer, used well

Rules: **it must be real**, you must be willing to accept it, and you should never present it as a threat.

> "I want to be transparent - I have another offer at *[range or company type]*, and I need to give them an answer by *[date]*. My preference is here, for *[a specific, true reason about the work]*. Is there room to close the gap? If there is not, I would rather know so I can decide honestly."

The structure matters: transparency, a genuine preference stated with a reason, a specific ask, and permission for them to say no. That last part is what keeps the relationship intact, and the relationship is the point - you may be about to work with these people, and a hard-edged negotiation is remembered for years.

**Never:** invent an offer (recruiters in a market talk, and it is asked about later), use it to extract a raise from your current employer without intending to stay, or let a deadline you did not need to accept force a decision. It is legitimate to ask the other company for an extension, and they usually grant it.

### Q217. A low offer for the best role you have seen `[T]`

Separate the two questions before you respond, because conflating them is how people talk themselves out of a good job or into a bad deal.

1. **Is the gap fixable?** Make one clear, prioritized ask with a reason that is not "I want more": market data, the competing offer, or the scope being larger than the band implies. "Based on the scope we discussed - owning the platform direction across four teams - the offer is below what I have seen for that remit. If you can move the base to *[X]* or bridge it with a sign-on, I am ready to accept."
2. **If it does not move, is the role still worth it?** Answer this honestly and in advance of the conversation. Write down the number below which you would decline *before* you hear their response, so the decision is not made under social pressure.

**The middle paths worth asking for** when the band is genuinely hard: a sign-on covering the first-year gap, an accelerated review at six months with written criteria, a level review at twelve months, or additional equity.

**The thing to avoid:** accepting a number you resent. It surfaces in month eight as disengagement, and it is the most common cause of a short tenure that then costs you on the next resume.

### Q218. Evaluating an offer against what you actually want

Decide **the one thing** before you have offers, or comparison becomes rationalization.

At nineteen years the candidates are usually: scope and decision rights; learning in a specific direction (AI depth, scale, a new domain); people you want to work with and learn from; total compensation; stability; or time. **Pick one primary and one secondary, write them down, and score offers against those** rather than against each other.

Then apply three tests: the **twelve-month test** - what will be true about you in a year that is not true now, and is that the direction you want; the **regret test** - which decision would you be more annoyed about in two years; and the **downside test** - if the role is worse than advertised, what have you still gained? A role that pays well and teaches you nothing fails the last one badly.

**The trap** is comparing on the dimension that is easiest to measure. Compensation is a single number and scope is a paragraph, so compensation dominates spreadsheets - which is precisely why the primary criterion has to be written down first.

### Q219. Declining while keeping the door open

Fast, direct, warm, and without a critique. Slow declines and vague ones are what damage relationships, not the decline itself.

> "Thank you - and thank you for the way the whole process was run, which I genuinely appreciated. I have decided to accept another role; the deciding factor was *[a true, non-comparative reason - the domain, the scope, the timing]*. I have enjoyed the conversations with you and *[name]*, and I would like to stay in touch. If things change on either side, I would be glad to talk again."

The mechanics: **tell them by phone or a call if you have built a relationship with the manager**, then confirm by email; do it as soon as you have decided rather than at the deadline; give a reason that is true but not a comparison ("the other offer paid more" invites a counter and a negotiation you have already decided against); and do not offer feedback on their process unless asked, in which case be brief and kind.

**The genuinely valuable follow-through:** connect with the manager afterwards and stay in touch once or twice a year. A large share of senior roles come from exactly this - a manager who liked you two years ago.

### Q220. The two weeks between the loop and the decision

- **Keep other processes alive.** Nothing weakens your position or your judgement like a single option, and momentum is expensive to rebuild if this falls through.
- **Do the diligence you could not do while selling yourself:** talk to people who have left, read the engineering blog and check whether the practices described match what you were told, look at their public repositories and job postings for what they are really building.
- **Prepare the negotiation** while you are unemotional (Q215, Q218). Write down your number and your primary criterion now, not after the offer arrives.
- **Follow up once, at the point they said they would decide** - not before. One short message, no chasing.
- **Debrief yourself while it is fresh.** Write down every question you were asked and every answer you were unhappy with; this is the most valuable input to your next loop and it evaporates in a week.
- **Do not spiral.** Reading the silence is not a source of information. Assume nothing until they tell you, and use the fortnight on the two items above.

### Q221. A ten-day final ramp `[A]`

The constraint: ten days, a job, and no time for new material. **This is a consolidation and rehearsal plan, not a learning plan** - saying that is half the answer.

| Days | Focus | Output |
| --- | --- | --- |
| 1 | The specific loop: research the company's stack and problems, then map which packs it will draw on and pick the three most likely rounds | A one-page target list. Everything after this is aimed at it |
| 2-3 | Cheatsheets only, for the three target packs, plus [cheatsheet.md](cheatsheet.md) here. Speak the answers rather than reading them | A list of the ten things that came out hesitantly |
| 4 | Those ten weak points, from the relevant `answers.md`. No breadth | The gaps closed or explicitly abandoned |
| 5 | Two full design rounds, recorded, timed, no pausing (Q72-Q77) | Self-scored with the rubric in [mocks/scoring-sheet.md](mocks/scoring-sheet.md) |
| 6 | Story bank: five stories at two minutes and at six, out loud, with the numbers (Q185) | A one-page number sheet for the day |
| 7 | One full loop from [mocks/](mocks/README.md), end to end, with the breaks | The list of what degraded in the afternoon (Q204) |
| 8 | The single weakest round from day 7, re-run with a different question | - |
| 9 | Reverse interview and negotiation rehearsal (Q208, Q214), plus logistics: kit, links, room, water, printed number sheet | Questions written per interviewer |
| 10 | Light. Re-read the cheatsheets once, one two-minute story, sleep | - |

**The rules that make it work:** no new topics after day 4; everything spoken, nothing read silently; and day 10 is deliberately light, because cramming the day before degrades the afternoon rounds more than the extra material helps.

### Q222. Your "what I want next" statement, defended `[A]`

The statement is two or three sentences, specific enough to exclude things:

> "I want a principal role where the architecture direction and the engineering standards across several teams are mine to own, in a system big enough that the decisions have consequences. I want the AI work to be part of the mandate rather than something I create room for, and I want to be technically hands-on enough that I keep the credibility to make those calls. What I am not looking for is a management track or a single-team scope."

**The hostile questions it must survive**, and the honest answers:

- *"That sounds like a management job you do not want the accountability for."* No - the accountability I want is for the technical outcome and the standard. I have carried the pager and I have owned failures; what I do not want is headcount and performance management, and those are different things (Q19).
- *"What if the standards work is fifty percent politics?"* It always is, and that is not a complaint - influence without authority is the job, and the evidence that I can do it is *[the artifact that outlived me]* (Q180).
- *"Everyone says they want scope. Why should we give it to you on day one?"* You should not. I would expect to earn it in the first ninety days by delivering something visible (Q22), and I would expect you to hold me to that.
- *"What if the AI work dries up?"* Then I want to be somewhere with the other two things, which is why the scope clause comes first in that sentence. The AI part is where I want to grow, not the condition of my joining.
- *"Is this really about compensation?"* No, and I will be straight that compensation matters - but the thing that would make me leave a well-paid role is scope, and it is the thing I would leave *for* (Q218).

**The test of the statement:** if it does not exclude any real job, it is not a statement, it is a wish. The exclusions are what make it credible under questioning.

