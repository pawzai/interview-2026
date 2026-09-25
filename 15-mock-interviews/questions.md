# Mock Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the pack that owns the technical depth. This pack does not re-teach any of it.

**What this pack is about.** Packs `01` to `11` establish that you know the material. This one is about the forty-five minutes in which you have to prove it to a stranger who is taking notes. Every question here is about **performance under interview conditions**: how a round is scored, how a follow-up ladder is climbed, what a wrong answer costs and how it is recovered, how a design round is driven, and how a story is told so that the interviewer can write down evidence rather than an impression.

The answers in [answers.md](answers.md) are **grading keys**, not lessons. Each one gives what a strong answer must contain, the follow-ups the interviewer will ask next, the red flags, and a pointer to the pack that owns the mechanism. Q72-Q77 are run as full design rounds in [scenario-questions.md](scenario-questions.md). Q186-Q191 have no scripted answer on purpose - they must be your own stories. The full timed loops are in [mocks/](mocks/README.md).

---

## 1. How a principal-level loop is run and scored

> Assumed known: the answer frameworks in [../01-java/README.md](../01-java/README.md) - the four-layer technical answer, CIDER and STAR-L.

1. `[C]` What is a hiring loop actually deciding at principal level, and why is "can this person do the job" not the question being asked?
2. `[D]` Name the round types in a typical principal, lead or architect loop and the single signal each round owns.
3. `[D]` What happens in a debrief, and how does a hiring decision actually get made when interviewers disagree?
4. `[T]` Two interviewers say strong hire and one says no hire with a specific example. What usually happens, and what does that imply about where to spend your preparation?
5. `[D]` What does leveling mean in practice, and what evidence in an interviewer's notes moves a candidate from senior to principal?
6. `[D]` Interviewers are trained to record evidence rather than impressions. What does a usable piece of evidence look like, and how do you hand them one?
7. `[C]` What four things is every interviewer scoring, regardless of the round's nominal topic?
8. `[T]` You answered every question correctly and still got a no hire. Give the three most common causes.
9. `[D]` How should the time inside a 45-minute round be budgeted, and what is the single most common misallocation?
10. `[D]` What is a mock interview for, and what makes a mock worthless?
11. `[D]` How do you self-score a mock with no partner, and what exactly do you record?
12. `[T]` You have run the same mock three times and your score improved each time. What is the likely artifact, and how do you control for it?
13. `[A]` Design a six-week mock schedule across the eleven technical packs, given three sessions a week and a full-time job.
14. `[A]` Design a calibration process with a peer outside your domain so that their score carries information.

---

## 2. Recruiter and hiring-manager screen

> Assumed known: your own history - Nittany Technologies 2007-2010, Verizon India 2010-2022, Sonata Software 2022-present, and the story bank in [../01-java/README.md](../01-java/README.md).

15. `[C]` Give a 90-second introduction covering 19 years, three companies, .NET into Java, and AI from 2024, that ends somewhere useful for the interviewer.
16. `[D]` "Walk me through your resume." Structure it, and say what the interviewer is listening for at each transition.
17. `[T]` "You have been at Sonata since 2022 - why are you looking?" Answer it without criticizing the employer and without sounding evasive.
18. `[D]` "Why this role?" when a recruiter found you and you know almost nothing about the company.
19. `[T]` Nineteen years and no manager title. How do you frame the principal track so it reads as a choice rather than a ceiling?
20. `[D]` How do you present the .NET-to-Java transition as an asset, and what makes the same story sound like a gap?
21. `[D]` "What is your current compensation?" What do you say, what do you never say, and what changes if the jurisdiction bans the question?
22. `[D]` The hiring manager asks what you would do in your first 90 days. What structure works when you do not yet know the systems?
23. `[T]` "Are you still hands-on?" at 19 years of experience. What proves it, and which claims actively hurt you?
24. `[D]` The recruiter screen includes three light technical questions. What is that segment really testing?
25. `[D]` How do you establish the real scope of the role before you invest four hours in a loop?
26. `[T]` The title says Principal Engineer but the job description reads like a senior contractor role. How do you probe that in the screen without insulting anyone?
27. `[A]` The hiring manager says the team is "moving from a monolith to microservices". Turn that one sentence into five questions that change your whole approach to the loop.
28. `[A]` Position the same 19-year history for three different roles: platform principal, solution architect, and AI engineering lead.

---

## 3. Java and Spring deep-dive round

> Assumed known: [../01-java](../01-java/questions.md) and [../02-spring](../02-spring/questions.md) in full. This category is about how that material is examined, not what it says.

29. `[C]` The round opens with "tell me about `HashMap`". How do you turn a shallow prompt into principal-level evidence in 90 seconds without lecturing?
30. `[D]` The interviewer asks "why?" three times in a row about `@Transactional`. Map the three levels you must have ready before the round starts.
31. `[T]` You are asked about a Java feature you have read about but never used in production. What answer scores, and what answer fails?
32. `[D]` "How would you find a memory leak in a running service?" What does the interviewer want to hear in the first sentence?
33. `[D]` Concurrency questions at this level are rarely about `synchronized`. What are they actually about, and how do you steer toward it?
34. `[T]` The interviewer states something about the Java memory model that is wrong. Play out the next 60 seconds.
35. `[D]` "Virtual threads - would you use them?" How do you avoid both the hype answer and the dismissive answer?
36. `[D]` Which three Spring mechanisms must you be able to draw from memory, and what does failing to draw them signal?
37. `[D]` "Why Spring Boot rather than plain Spring?" Give the answer everyone gives, then the one that scores.
38. `[T]` You are asked to walk the Spring Security filter chain and you blank on the filter order. Recover in a way that costs you nothing.
39. `[D]` A code-reading question: 30 lines with a subtle bug. What is your reading order and what do you say while reading?
40. `[D]` "How would you test that?" is appended to every one of your answers. What is being probed, and what makes the third repetition easier than the first?
41. `[D]` JPA and N+1: how do you answer so it is a production story rather than a textbook definition?
42. `[T]` "Do you use Lombok? Field injection? Checked exceptions?" How do you answer an opinion question when you do not know the interviewer's opinion?
43. `[A]` You are asked to design an internal library API that forty teams will depend on. What is the round actually scoring?
44. `[A]` Defend a Java and Spring stack choice against an interviewer who wants to hear why you would not use Go.

---

## 4. Distributed systems and microservices round

> Assumed known: [../03-microservices](../03-microservices/questions.md) in full.

45. `[C]` "How do you decide a service boundary?" Give the 60-second answer that earns the follow-up you want.
46. `[D]` The exactly-once question. How do you answer it correctly without sounding pedantic?
47. `[T]` The interviewer says "we use two-phase commit across our services". How do you disagree without spending your credibility?
48. `[D]` The interviewer conflates saga and outbox. Separate them in two sentences, then say why the confusion is common.
49. `[D]` "Tell me about a distributed system failure you debugged." What structure makes this land as evidence rather than a war story?
50. `[D]` "We use an idempotency key." Take that answer down three levels of follow-up and say what each level tests.
51. `[T]` You are asked how you would migrate a monolith and you have ten minutes. What do you deliberately leave out, and how do you signal that you left it out on purpose?
52. `[D]` Retries and circuit breakers: what makes an answer here mediocre, and what single addition makes it senior?
53. `[D]` "How do services find each other?" looks like a screening question. Where does the depth actually live and how do you get there?
54. `[D]` How do you show you have operated a message broker rather than read about one?
55. `[T]` "Do you version your APIs?" Everyone says yes. What is the follow-up, and which answer survives it?
56. `[D]` Consistency questions: how do you avoid reciting CAP and still answer the question that was asked?
57. `[D]` Which single anecdote covers tracing, sampling and cardinality at once, and why is one anecdote better than three?
58. `[A]` The interviewer asks you to decompose their actual product live. How do you run that with no domain knowledge?
59. `[A]` Argue against splitting a service, in front of an interviewer whose company has just finished splitting theirs.

---

## 5. System design round

> Assumed known: [../04-system-design](../04-system-design/questions.md) in full, including the fifteen worked designs. This category is about running the round.

60. `[C]` The first four minutes of a design round. What must happen, in what order, and what must not?
61. `[D]` How do you extract requirements when the interviewer is deliberately vague, and how many questions is too many?
62. `[D]` Estimation out loud: which numbers must be in your head, and how precise do they need to be?
63. `[T]` The interviewer says "assume infinite scale, do not worry about numbers". What is the correct response?
64. `[D]` How do you drive the whiteboard so the interviewer is following your reasoning rather than watching you draw?
65. `[D]` When do you go deep on one component versus keeping breadth, and who gets to decide?
66. `[T]` You are 30 minutes in and have not written a single number. What has gone wrong, and how do you recover without restarting?
67. `[D]` How do you present a data model in a design round without losing fifteen minutes to it?
68. `[D]` The interviewer injects a new requirement at minute 35. What is being tested, and what is the wrong instinct?
69. `[D]` How do you cover failure modes and SLOs without turning the round into an operations lecture?
70. `[T]` "Would you use Kafka here?" What is the trap in a component-name question, and how do you defuse it?
71. `[D]` The last three minutes of a design round. What do you say, and what do you write down?
72. `[A]` Design round, 45 minutes, run end to end: a multi-tenant document processing platform.
73. `[A]` Design round, 45 minutes, run end to end: real-time notification and fanout for twenty million users.
74. `[A]` Design round, 45 minutes, run end to end: migrating a telecom-scale nightly batch pipeline to streaming.
75. `[A]` Design round, 45 minutes, run end to end: an AI assistant embedded in an existing enterprise SaaS product.
76. `[A]` Design round, 45 minutes, run end to end: a global API platform with regional data residency requirements.
77. `[A]` Design round, 45 minutes, run end to end: rebuilding an on-premise Java monolith on AWS against a fixed budget and a hard date.

---

## 6. Cloud and AWS round

> Assumed known: [../05-aws](../05-aws/questions.md) and [../05-aws/core-services](../05-aws/core-services/questions.md).

78. `[C]` "Walk me through what happens when a request hits your AWS architecture." What shape of answer is expected?
79. `[D]` The interviewer asks which compute you would choose. What decision tree do you say out loud?
80. `[T]` "Lambda is cheaper." How do you handle a claim that is true only within a range?
81. `[D]` IAM questions at architect level: what separates a real answer from a console-driven one?
82. `[D]` VPC and connectivity: what must you be able to draw without hesitation, and what is safe to defer?
83. `[D]` "How do you do multi-region?" How do you answer in a way that proves you know what it costs?
84. `[T]` You are asked about an AWS service you have never used. Bound the answer honestly and still score.
85. `[D]` What makes a cost answer credible, and what makes it sound like a slide?
86. `[D]` "How do you deploy infrastructure?" Terraform, CDK or CloudFormation - what is actually being probed by the question?
87. `[D]` How do you use Well-Architected in an answer without reciting the pillars?
88. `[T]` The interviewer's own architecture has a single-AZ RDS instance in it. Do you point it out, and how?
89. `[D]` Quotas, throttling and limits: which anecdote proves operational experience in one minute?
90. `[A]` You are given an AWS architecture on a whiteboard and twenty minutes to review and improve it.
91. `[A]` Justify an on-premise-to-AWS migration to a finance-facing stakeholder who is part of the loop.

---

## 7. Data and database round

> Assumed known: [../06-database](../06-database/questions.md) in full.

92. `[C]` "Write me a query." What is the interviewer actually reading while you type?
93. `[D]` Indexing questions come in three levels of depth. Name them and say what each one is filtering for.
94. `[T]` "Why is this query slow?" with no schema and no plan. What do you ask, in what order?
95. `[D]` Transactions and isolation: how do you answer without reciting the anomaly table?
96. `[D]` SQL versus NoSQL: how do you avoid the religious answer and still take a position?
97. `[D]` "How would you shard this?" What has to be established before you are allowed to answer?
98. `[T]` The interviewer proposes caching as the fix for a write-heavy problem. How do you redirect without contradicting them flatly?
99. `[D]` Schema migration on a live system: what detail proves you have actually done it?
100. `[D]` Replication lag: which anecdote lands, and what number must be in it?
101. `[T]` "How big can PostgreSQL get?" How do you answer a question with no correct number?
102. `[A]` Live modeling exercise: a subscription billing domain, on a whiteboard, in twenty-five minutes.
103. `[A]` You are asked to choose the datastore for five different workloads in ten minutes.
104. `[D]` How do you carry one database story across the design, coding and deep-dive rounds without repeating yourself?

---

## 8. DevOps, delivery and incident-command round

> Assumed known: [../07-devops](../07-devops/questions.md) in full.

105. `[C]` "Walk me through your CI/CD pipeline." What level of detail is expected, and where do most candidates stop too early?
106. `[D]` An incident-command round: what is the structure of a good answer, and where does CIDER fit?
107. `[T]` "What was your worst outage?" How much blame do you take, and what happens if you take none?
108. `[D]` How do you use the DORA metrics without sounding like a consultant?
109. `[D]` Kubernetes questions when you are not a Kubernetes specialist. Where exactly do you draw the line?
110. `[D]` "How do you roll back?" Take it down three levels of follow-up.
111. `[D]` On-call questions are leadership questions in disguise. What are they really asking?
112. `[T]` The interviewer describes their deployment process in one sentence and asks how you would improve it. What is the trap?
113. `[D]` Observability round: what does a strong answer contain beyond a list of tools?
114. `[D]` Secrets management: what answer survives a security-minded follow-up?
115. `[D]` Canary versus blue-green: what makes the answer specific to their constraints rather than generic?
116. `[T]` "We deploy once a quarter and it works for us." Do you challenge it, and how?
117. `[A]` A live incident simulation: alerts firing, partial information, the interviewer playing your on-call engineer.
118. `[A]` You are asked to define a platform team's charter and its success metrics.

---

## 9. AI round: GenAI, RAG and agents

> Assumed known: [../08-genai](../08-genai/questions.md), [../09-rag](../09-rag/questions.md) and [../10-ai-agents](../10-ai-agents/questions.md).

119. `[C]` "You say you do AI - what have you actually built?" Structure ninety seconds that survives a skeptical follow-up.
120. `[D]` How do you separate GenAI, RAG and agent material out loud so the interviewer can see you know the boundaries?
121. `[T]` "Isn't this all just prompt engineering?" Answer without being defensive and without overclaiming.
122. `[D]` Token and cost arithmetic out loud: what must you be able to compute in your head, in a round, with no calculator?
123. `[D]` A RAG design round: the first five decisions, in order, and why that order.
124. `[T]` The interviewer's team built RAG and the quality is poor. Diagnose it live with three questions.
125. `[D]` "How do you evaluate it?" ends most AI interviews. What is the complete answer?
126. `[D]` Hallucination questions: how do you answer with mechanism rather than reassurance?
127. `[D]` When do you say "do not build an agent", and how do you say it to an interviewer whose team is building one?
128. `[T]` "What model do you use?" Why is the answer not a model name, and what is it instead?
129. `[D]` How do you raise prompt injection in an answer without derailing the round into security?
130. `[D]` How do you present AI work starting in 2024 as depth rather than a recent pivot?
131. `[D]` When is bringing up Java and Spring AI an advantage in an AI round, and when does it read as a limitation?
132. `[T]` The interviewer is more current on models than you are. How do you keep credibility?
133. `[A]` Design round: add an AI capability to an existing product with a 300 millisecond latency budget.
134. `[A]` You are asked how you would set AI engineering standards for an organization of 300 engineers.

---

## 10. Security round

> Assumed known: [../11-security](../11-security/questions.md) in full.

135. `[C]` "How do you secure an API?" Give the layered ninety-second answer.
136. `[D]` OAuth 2.1 and OIDC: which parts must you explain without notes, and which are fair to look up?
137. `[T]` "Do you store JWTs in local storage?" Answer the trap question.
138. `[D]` Threat modeling live: how do you run STRIDE over their system in eight minutes?
139. `[D]` Secrets, key rotation and KMS: what proves operations rather than reading?
140. `[T]` The interviewer asks about a CVE you have never heard of. Play out the next minute.
141. `[D]` "How do you handle authorization?" Where does the depth actually live, and how do you get there quickly?
142. `[D]` Supply chain security: what is the concrete evidence of practice rather than awareness?
143. `[D]` How do you discuss a security incident you were part of without breaching confidentiality?
144. `[D]` AI security questions inside a security round: what is genuinely specific to LLM systems?
145. `[T]` "Is our current design secure?" asked about a diagram with three obvious holes and one subtle one. How do you sequence what you say?
146. `[A]` You are asked to define the secure SDLC for a team that has none, with a delivery deadline unchanged.
147. `[A]` Argue for a security investment to a stakeholder whose only metric is delivery speed.

---

## 11. Coding and pairing round

> Assumed known: [../01-java](../01-java/questions.md) language material. This category is about the round, not the algorithm.

148. `[C]` The problem in a principal-level coding round is usually easy. What is the round actually scoring?
149. `[D]` How do you narrate while coding without slowing to a crawl?
150. `[D]` The first three minutes, before you type anything. What happens?
151. `[T]` You see the optimal solution immediately. Do you write it straight away?
152. `[D]` Tests in a 45-minute coding round: how many, and when do you write them?
153. `[D]` Naming, structure and error handling under time pressure. What do you keep and what do you consciously drop?
154. `[T]` You are stuck at minute 25. What do you do, in order?
155. `[D]` The interviewer suggests an approach you believe is wrong, while you are coding. How do you handle it?
156. `[D]` Complexity analysis: when do you volunteer it, and how precise does it need to be?
157. `[D]` A pairing round on their real codebase. How do you start, and what do you ask for?
158. `[T]` Your solution fails on an edge case the interviewer supplies. What is the recovery sequence?
159. `[D]` Streams versus loops, `Optional`, records, exceptions - which Java choices signal what to a reviewer?
160. `[D]` A take-home instead of a live round: how do you scope the time, and what do you include that nobody asked for?
161. `[A]` Design-and-implement: a rate limiter, sixty minutes, production quality expected.
162. `[A]` Refactoring exercise: two hundred lines of legacy Java, improve it live and justify every change.

---

## 12. Architecture review and code review rounds

> Assumed known: [../03-microservices](../03-microservices/questions.md) and [../04-system-design](../04-system-design/questions.md).

163. `[C]` You are handed an architecture diagram and asked "what do you think?" How do you open?
164. `[D]` In what order should you critique a design, and why does the order change the interviewer's impression more than the content?
165. `[T]` The design is genuinely good. What do you do with the remaining forty minutes?
166. `[D]` How do you criticize an architecture when its author is in the room and is on your interview panel?
167. `[D]` A code review round: what do you comment on first, and what do you deliberately not comment on?
168. `[D]` How do you distinguish a blocking comment from a preference, out loud, so the difference is unmistakable?
169. `[T]` You find a genuine security flaw in their production design during the review. How do you raise it?
170. `[D]` What do you ask before critiquing anything, and how do you ask it without stalling?
171. `[D]` How do you demonstrate mentoring ability in a code review round?
172. `[T]` The code has twenty problems and you have thirty minutes. What is the selection strategy?
173. `[D]` What does a principal-level reviewer notice that a strong senior does not?
174. `[A]` Review an event-driven design with a hidden ordering assumption, and run the whole conversation.
175. `[A]` You are asked to write your organization's code review standard, live, in twenty minutes.

---

## 13. Behavioural and leadership under pressure

> Assumed known: STAR-L and the story bank in [../01-java/README.md](../01-java/README.md), and the competency model and story construction in [../12-behavioural](../12-behavioural/README.md), which owns the substance of these answers. This category is about delivering them under interview conditions. Q186-Q191 have no scripted answer - they are your stories.

176. `[C]` STAR-L in two to three minutes. What is the time budget per letter, and which letter do candidates overrun?
177. `[D]` How do you quantify a Result when the numbers are confidential or you no longer remember them?
178. `[T]` "Tell me about a failure." How much failure is the right amount, and what does too little signal?
179. `[D]` "Tell me about a conflict with a colleague." What makes an answer credible rather than sanitized?
180. `[D]` Influence without authority: what evidence actually counts at principal level?
181. `[D]` How do you tell a story where the team succeeded while making your own contribution unmistakable?
182. `[T]` The interviewer asks for a second example of the same competency. What is happening, and what does a weak second example cost you?
183. `[D]` How do you handle a behavioural question about a situation you have genuinely never been in?
184. `[D]` Disagree and commit: what does an answer look like that shows both halves rather than only the disagreement?
185. `[D]` How do you build a story bank that covers a competency matrix without memorizing ten separate scripts?
186. The largest system you architected end to end, told first in two minutes and then in eight.
187. A production incident you led, told as an incident-command story rather than a debugging story.
188. A technical decision you lost, and how you supported the outcome afterwards.
189. Mentoring a struggling engineer to independence, with the evidence that it worked.
190. A time you chose the boring solution and were proved right, and one where you were proved wrong.
191. Driving a standard or a platform decision across teams you did not own.

---

## 14. Bar raiser, curveballs and recovery

> Assumed known: everything above. This is the category that decides borderline loops.

192. `[C]` What is a bar raiser optimizing for, and why is it not your technical depth?
193. `[D]` You gave a wrong answer twenty minutes ago and have just realized it. What do you do?
194. `[T]` "I do not think that is right." The interviewer is wrong. Play out the next two minutes.
195. `[D]` How do you say "I do not know" in a way that adds evidence rather than subtracting it?
196. `[D]` The interviewer is silent and gives you no signal at all. How do you adapt?
197. `[T]` A hostile or visibly distracted interviewer. What is actually in your control?
198. `[D]` "How many ATMs are there in India?" Why is this asked at principal level, and how do you run it?
199. `[D]` "What would you do differently if you could redo the last five years?" What is this question for?
200. `[T]` "Why should we hire you over someone with ten years of pure Java?" Answer it without disparaging the alternative.
201. `[D]` A rapid-fire round, twenty questions in twenty minutes. How does your strategy change?
202. `[D]` A question that spans three packs at once. How do you choose which thread to pull?
203. `[T]` You realize mid-answer that you are four minutes into a ninety-second question. Recover.
204. `[D]` Energy management across a five-round day: what actually degrades, and what counters it?
205. `[A]` Design your own bar raiser round for a principal candidate and say what each question is for.
206. `[A]` Critique your own strongest project as though you were the bar raiser trying to sink it.

---

## 15. Reverse interview, debrief signals, offer and negotiation

> Assumed known: your own criteria for the next role. The final ramp and the negotiation questions are worth rehearsing out loud exactly like the technical ones.

207. `[C]` "Do you have questions for us?" How many, and what does each one signal?
208. `[D]` Give five questions that make a hiring manager reconsider your level upward.
209. `[D]` What do you ask to find out whether a principal role has real scope or is a retitled senior role?
210. `[T]` The answers to your questions reveal a dysfunctional organization. Do you continue the loop?
211. `[D]` What do you ask an engineer on the team that you would never ask the manager?
212. `[D]` What can you read from how the loop itself was run?
213. `[D]` The follow-up note: worth sending, and what belongs in it?
214. `[T]` They ask for your compensation expectation before you have any signal about their range. What do you say?
215. `[D]` Negotiating at principal level: which levers exist besides base salary, and which are actually movable?
216. `[D]` A competing offer: how do you use it without damaging the relationship you are about to join?
217. `[T]` The offer is below your number but the role is the best one you have seen. How do you run that conversation?
218. `[D]` How do you evaluate an offer against the one thing you actually want next?
219. `[D]` Declining an offer while keeping the door genuinely open.
220. `[D]` What do you do in the two weeks between the final round and the decision?
221. `[A]` Design your own ten-day final ramp before a loop you care about, using these packs.
222. `[A]` Write your "what I want from the next role" statement and defend it under hostile questioning.
