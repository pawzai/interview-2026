# Behavioural Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line. The answer frameworks - the four-layer technical answer, CIDER and **STAR-L** - are defined once in [../01-java/README.md](../01-java/README.md) and are not restated here.

**What this pack is about.** The substance of a leadership answer: which competency a question is probing, what evidence satisfies it, and how a story from Nittany Technologies, Verizon India or Sonata Software is built so that the interviewer can write down a fact. The *delivery* of that story under interview conditions - timing, follow-up ladders, recovery - belongs to [../15-mock-interviews](../15-mock-interviews/questions.md), Categories 13 and 14.

Answers are **hybrid**. Technique questions get a coaching key; story questions get a first-person STAR-L skeleton with the numbers left as placeholders like *[p99 before]*. **Q43-Q48 have no scripted answer on purpose** - they are your six core stories, and [scenario-questions.md](scenario-questions.md) Part C says how to build them.

---

## 1. What a behavioural round measures at principal level

> Assumed known: STAR-L from [../01-java/README.md](../01-java/README.md), and the competency matrix in [README.md](README.md).

1. `[C]` What is a behavioural round actually measuring, given that nobody can verify a word of what you say?
2. `[C]` Name the nine competencies a principal-level behavioural loop probes, and the one question behind each.
3. `[D]` How does an interviewer convert a story into a score, and what does the note they write actually look like?
4. `[T]` Two candidates tell the same story. One is scored senior and one principal. What differed?
5. `[D]` What is a second-order effect, and why does its absence cap a story at senior level?
6. `[D]` "What would have happened if you had not been there?" What is this counterfactual testing, and how do you answer it without sounding arrogant?
7. `[D]` Why do interviewers ask for specific named people in a story, and what does "the team decided" signal?
8. `[T]` Your best story is your most technically impressive one. Why is that usually the wrong story to lead with in a behavioural round?
9. `[D]` What is the difference between scope of work and scope of influence, and which one is being levelled on?
10. `[D]` How does a behavioural round differ when run by a hiring manager, a peer, a skip-level and a bar raiser?
11. `[T]` The interviewer nods along and asks no follow-ups at all. What has probably happened?
12. `[D]` What does an interviewer do with a story that has no conflict, no mistake and no cost in it?
13. `[A]` You are given one story and must demonstrate three competencies with it. How do you choose which three, and how do you signal the pivot?
14. `[D]` Why is "tell me about a time" phrased in the past tense, and what happens when you answer hypothetically?
15. `[T]` How much of the technical detail belongs in a behavioural answer, and what is the failure mode in each direction?
16. `[A]` Design the behavioural round you would run for a principal candidate, and say what each question is for.

---

## 2. Story construction and evidence

> Assumed known: STAR-L and its time budget. The timing mechanics are owned by [../15-mock-interviews](../15-mock-interviews/questions.md) Q176.

17. `[C]` What must every story contain to be usable as evidence? Give the checklist.
18. `[D]` How long should the Situation be, and what is the test for whether you have said too much?
19. `[D]` The Task step is the one candidates skip entirely. What is it for, and what breaks without it?
20. `[D]` How do you keep "Action" in the first person without sounding like you took credit for a team's work?
21. `[T]` How do you quantify a Result when the numbers are confidential, lost, or were never measured?
22. `[D]` What kinds of numbers actually land: absolute, relative, or cost? Give the ordering and why.
23. `[T]` Your most impressive result was mostly caused by something outside your control. How do you tell it honestly and still get credit?
24. `[D]` What separates a Learning that scores from one that sounds like a platitude?
25. `[D]` How do you show that a Learning is real rather than retrofitted?
26. `[D]` What is a story spine, and why memorize it instead of the story?
27. `[D]` How do you compress a six-minute story into two minutes without turning it into a summary?
28. `[T]` The interviewer interrupts your Situation with "so what did you do?" What has gone wrong and how do you recover the structure?
29. `[D]` How do you handle a story where the outcome was genuinely bad?
30. `[D]` Where should a story's technical depth live so that it is available on demand but not in the way?
31. `[T]` How recent must a story be, and what is the cost of a great story from 2013?
32. `[D]` How do you tell a story about a multi-year programme without the timeline swallowing the answer?
33. `[A]` Build a scoring rubric for your own stories that a non-technical friend could apply.
34. `[A]` You have nineteen years of material and can prepare eight stories. What selection criteria maximize coverage?

---

## 3. Building the story bank - one story, many faces

> Assumed known: the ten-story seed list in [../01-java/README.md](../01-java/README.md). The method is expanded in [scenario-questions.md](scenario-questions.md) Part C.

35. `[C]` What is a "face" of a story, and why does eight stories cover thirty questions?
36. `[D]` Take one migration story and list every competency it can legitimately serve. Where is the line into stretching it?
37. `[D]` How do you signal a pivot when reusing a story the interviewer has already heard part of?
38. `[T]` You have used the same story twice in one loop with different interviewers. Is that a problem?
39. `[D]` How do you build a coverage matrix of stories against competencies, and what does a hole in it look like?
40. `[D]` What do you do about a competency you genuinely have no story for?
41. `[D]` How do you keep the bank fresh - what is the refresh cadence and what triggers a rewrite?
42. `[A]` Design the one-page sheet you would review thirty minutes before a loop, and justify what is on it.
43. Your largest system architected end to end: scale, your decisions, and what you would build differently now.
44. A production incident you led, told as incident command with a real timeline.
45. A technical decision you lost, and how you supported the outcome afterwards.
46. Mentoring a struggling engineer to independence, with third-party-verifiable evidence.
47. Driving a standard or platform decision across teams you did not own.
48. The AI capability you shipped from 2024 onwards, with its cost and quality controls.

---

## 4. Ownership, scope and second-order impact

> Assumed known: the counterfactual test from Q6 and the second-order definition from Q5.

49. `[C]` "Tell me about a time you took ownership of something that was not your responsibility."
50. `[D]` What distinguishes ownership from heroics, and why is the heroic version a red flag at principal level?
51. `[D]` "Tell me about something you fixed that stayed fixed." What evidence proves the second half?
52. `[T]` You owned a system nobody wanted and kept it alive for three years. Is that a good story?
53. `[D]` "Describe a problem you found that nobody had asked you to look at."
54. `[D]` How do you demonstrate ownership of an outcome you did not personally deliver?
55. `[D]` "Tell me about a time you had to clean up someone else's mess." How do you do it without disparaging them?
56. `[T]` What is the difference between ownership and refusing to delegate, and how does an interviewer tell?
57. `[D]` "Give an example of a decision you made that you would not have been criticized for avoiding."
58. `[D]` How do you show ownership of a system's cost rather than only its behaviour?
59. `[D]` "Tell me about a commitment you made that turned out to be much harder than expected."
60. `[T]` "What is something broken today that you own and have not fixed?"
61. `[D]` How do you describe taking over a system you inherited and disagreed with, without spending the story on criticism?
62. `[A]` What does ownership look like across an organizational boundary, where the failing component belongs to another company or vendor?
63. `[D]` "Tell me about a time you deliberately let something fail."
64. `[A]` Argue the case that a principal engineer's real unit of ownership is a class of problem rather than a system.

---

## 5. Influence without authority

> Assumed known: the influence evidence bar in [README.md](README.md) - named minds changed, plus a mechanism that made the right way the easy way.

65. `[C]` "Tell me about a time you influenced a decision without having the authority to make it."
66. `[D]` What kinds of evidence actually count as influence at principal level, and which are commonly offered but worthless?
67. `[D]` How do you get a standard adopted by teams that do not report to you and do not want it?
68. `[T]` The standard was adopted because a director mandated it after you asked them to. Does that count?
69. `[D]` "Describe a time you changed a senior person's mind."
70. `[D]` What do you do about the team that never adopts it, and how do you talk about them in an interview?
71. `[D]` How do you make the right way the easy way? Give concrete mechanisms rather than the slogan.
72. `[T]` Your proposal was rejected, then adopted eighteen months later by someone else. How do you tell that story?
73. `[D]` "Tell me about a time you built consensus among people who disagreed with each other."
74. `[D]` How do you influence through writing, and what makes a document that actually changes a decision?
75. `[D]` "Describe how you introduced a practice that outlived your involvement."
76. `[T]` How do you tell an influence story where the mechanism was mostly social - lunches, trust, relationships - without it sounding like politics?
77. `[D]` How do you handle influencing upward when the decision has effectively already been made?
78. `[D]` "Tell me about a time you had to sell a decision you only partly believed in."
79. `[D]` How do you influence a partner team whose incentives are genuinely opposed to yours?
80. `[A]` Design the adoption plan for a cross-team standard, from proposal to the point where it is invisible.
81. `[T]` "How do you know your influence was the cause rather than the coincidence?"
82. `[A]` What changes about influence when the teams are in different countries, companies or time zones?

---

## 6. Conflict, disagreement and disagree-and-commit

> Assumed known: the tone bar - disagreement with the relationship intact. Interview-room disagreement with the interviewer is owned by [../15-mock-interviews](../15-mock-interviews/questions.md) Q194.

83. `[C]` "Tell me about a conflict with a colleague." What makes an answer credible rather than sanitized?
84. `[D]` What is the difference between a technical disagreement and a conflict, and why does the interviewer want the second?
85. `[D]` How do you tell a conflict story in which the other person was substantially in the wrong?
86. `[T]` Your conflict story ends with you being right. Why is that the weaker version, and what is the stronger one?
87. `[D]` "Disagree and commit": what does an answer look like that demonstrates both halves rather than only the disagreement?
88. `[D]` What does visible commitment actually look like after you lost the argument?
89. `[D]` "Tell me about a time you were overruled by someone more senior."
90. `[T]` How do you handle "tell me about a time you disagreed with your manager" without either sounding compliant or disloyal?
91. `[D]` "Describe a disagreement you resolved between two other people."
92. `[D]` How do you escalate a disagreement well, and what does a bad escalation look like?
93. `[D]` "Tell me about a time you had to give someone difficult feedback."
94. `[T]` "Tell me about feedback you received that you disagreed with." What is being tested?
95. `[D]` How do you disagree in writing - a review comment, a design doc thread - without it hardening?
96. `[D]` "Describe a situation where the disagreement was about values rather than facts."
97. `[T]` A colleague repeatedly undermines your technical decisions in front of others. How does that story get told?
98. `[D]` How do you re-open a decision you committed to when new evidence appears, without looking like you never committed?
99. `[A]` When is it correct to keep fighting a decision, and what is the test?
100. `[A]` Design the conflict-resolution protocol you would want a team of forty engineers to use for architectural disputes.

---

## 7. Failure, mistakes and accountability

> Assumed known: the accountability bar - a failure you name before being asked, with a systemic fix.

101. `[C]` "Tell me about a failure." How much failure is the right amount, and what does too little signal?
102. `[D]` What makes a failure story convincing, and what are the three fake failures interviewers hear constantly?
103. `[D]` How do you separate the personal fix from the systemic fix, and why does only one of them score?
104. `[T]` "Tell me about your biggest professional mistake." How do you pick one that is genuinely costly but does not disqualify you?
105. `[D]` "Describe a project that failed." How do you handle one where the cause was mostly organizational?
106. `[D]` How do you tell a failure story where you were not the primary cause but were accountable?
107. `[T]` What is the difference between accountability and self-flagellation, and where is the line in an answer?
108. `[D]` "Tell me about a time you were wrong about a technical decision and had to reverse it."
109. `[D]` How do you talk about a failure that involved another named person without blaming them?
110. `[D]` "What did you learn from it?" - what does a real answer look like, versus the standard one?
111. `[T]` "Tell me about a time you missed a deadline." What is actually being probed here?
112. `[D]` How do you describe a decision that was reasonable given what you knew and still turned out wrong?
113. `[D]` "Have you ever hidden or delayed bad news?" How do you answer honestly?
114. `[D]` What does a blameless postmortem look like when the cause really was a person's judgement?
115. `[A]` How would you build an engineering culture where failures surface early, and what evidence would tell you it worked?
116. `[A]` Critique your own strongest project as though you were trying to sink it.

---

## 8. Incident command and delivering under pressure

> Assumed known: incident mechanics from [../07-devops](../07-devops/questions.md) Category 11 - this category is about your conduct, not the runbook.

117. `[C]` "Walk me through a production incident you led." What is the shape of the answer?
118. `[D]` Why does the interviewer want incident command rather than debugging, and how do you tell the difference in your own story?
119. `[D]` What does taking command sound like out loud, and why does saying it matter?
120. `[T]` Why does mitigating before diagnosing score higher, and when is that the wrong instinct?
121. `[D]` How do you describe communicating during an incident - to whom, how often, and containing what?
122. `[D]` "Describe a decision you made during an incident with incomplete information."
123. `[D]` How do you show that the follow-up changed the class of failure rather than the instance?
124. `[T]` "Tell me about an incident you handled badly."
125. `[D]` How do you talk about an incident caused by your own change?
126. `[D]` "Describe a time you had to deliver under an impossible deadline." What is the honest answer?
127. `[D]` What do you say about what you cut, who you told, and when?
128. `[T]` "Have you ever pushed back on a deadline?" What separates a good pushback story from a complaint?
129. `[D]` How do you describe protecting a team from pressure without positioning yourself as their shield against management?
130. `[D]` "Tell me about a time you worked a sustained crunch." What is the trap in this question?
131. `[A]` How would you run a major incident spanning three teams and a vendor, and what would you do first?
132. `[A]` What does "operational maturity" mean as evidence in a story, and what number demonstrates it?

---

## 9. Growing people - mentoring, hiring and performance

> Assumed known: the growth bar - someone is now doing work you used to do.

133. `[C]` "Tell me about someone you mentored." What is the evidence that it worked?
134. `[D]` How do you build a before-and-after that a third party could verify?
135. `[D]` What does a mentoring story need that most of them lack?
136. `[T]` "Tell me about a mentee where it did not work out."
137. `[D]` How do you describe mentoring someone more experienced than you, or in a different specialism?
138. `[D]` "Describe how you delegated something you were better at than the person you gave it to."
139. `[D]` How do you show you scale through others rather than through output?
140. `[T]` What is the difference between mentoring, coaching, sponsoring and managing, and why does an interviewer care?
141. `[D]` "Tell me about a difficult performance conversation." How do you answer without a manager title?
142. `[D]` How do you handle a story about a strong engineer with a bad effect on the team?
143. `[D]` "Describe how you have raised the technical bar of a team."
144. `[D]` What does your interview process look like, and what signal do you personally own on a panel?
145. `[T]` "Have you ever argued to reject a candidate everyone else wanted to hire?"
146. `[D]` How do you onboard a senior hire, and what would you change about how you were onboarded?
147. `[D]` "Tell me about building a team's confidence after a bad quarter."
148. `[D]` How do you describe growing a peer rather than a junior?
149. `[A]` Design a twelve-month growth plan for a senior engineer stalled on the way to staff.
150. `[A]` What would you do in your first ninety days leading a team of engineers you did not choose?

---

## 10. Stakeholder and executive communication

> Assumed known: the upward-communication bar - bad news early, with options and a recommendation.

151. `[C]` "Explain a complex technical decision to a non-technical executive." Do it now, with a real one.
152. `[D]` What is the structure of an executive update, and how does it differ from a technical one?
153. `[D]` How do you deliver bad news to a stakeholder, and what makes the difference between early and late?
154. `[T]` "Tell me about a time you had to say no to an executive."
155. `[D]` How do you present options rather than a single recommendation, without abdicating the decision?
156. `[D]` "Describe a time you had to translate a business requirement into an architecture, and push back on part of it."
157. `[D]` How do you talk about cost and risk to someone who does not want to hear about either?
158. `[T]` The executive asks for a date and you do not have one. What do you say?
159. `[D]` "Tell me about a time a stakeholder changed the requirements late."
160. `[D]` How do you handle a stakeholder who goes around you to your team?
161. `[D]` "Describe how you have communicated a multi-quarter technical investment with no visible feature output."
162. `[T]` How do you describe a situation where the business decision went against your technical advice and turned out fine?
163. `[D]` What does a good written status update contain, and what makes one worthless?
164. `[D]` "Tell me about presenting to a customer or an audience outside your company."
165. `[A]` Draft the one-page memo you would send to a CTO recommending a significant architectural investment.
166. `[A]` How do you build credibility with a new stakeholder group in the first month?

---

## 11. Prioritization, saying no, and negotiating scope

> Assumed known: the judgement bar - a decision you deliberately did not make, or delayed, and why.

167. `[C]` "Tell me about a time you had to say no." What makes a no land well?
168. `[D]` How do you prioritize between two things that are both genuinely urgent and owned by different stakeholders?
169. `[D]` "Describe a time you cut scope to make a date."
170. `[T]` "Have you ever shipped something you knew was not good enough?"
171. `[D]` How do you decide what technical debt to pay and what to leave forever?
172. `[D]` "Tell me how you made the case for work with no visible customer value."
173. `[D]` What framework do you actually use to prioritize, and how do you avoid it sounding like a template?
174. `[T]` Everything is priority one and the person who set that is your skip-level. What do you do?
175. `[D]` "Describe a time you killed a project."
176. `[D]` How do you handle a request that is reasonable in isolation and disastrous in aggregate?
177. `[D]` "Tell me about a trade-off you made between speed and quality, and what it cost."
178. `[T]` How do you say no to a peer whose goodwill you need next quarter?
179. `[D]` How do you decide what not to do when you have surplus capacity rather than a shortage?
180. `[A]` Build the prioritization argument for spending a quarter of a team's capacity on reliability.
181. `[A]` What is the most expensive thing you have ever chosen not to build, and how did you defend it?

---

## 12. Ambiguity, change and starting from nothing

> Assumed known: CIDER from [../01-java/README.md](../01-java/README.md) - the Clarify step is the behaviour being probed here too.

182. `[C]` "Tell me about a time you had to make progress with unclear requirements."
183. `[D]` What do you do first when handed a problem with no defined scope, and how do you narrate it?
184. `[D]` "Describe the most ambiguous project you have worked on." What made it ambiguous rather than just hard?
185. `[D]` How do you make a decision that is expensive to reverse when the information will not arrive in time?
186. `[T]` How do you distinguish real ambiguity from someone declining to make a decision?
187. `[D]` "Tell me about a time the direction changed completely mid-project."
188. `[D]` How do you keep a team motivated through a change of direction you did not agree with?
189. `[D]` "Describe starting something from nothing - no team, no precedent, no requirements."
190. `[D]` How do you set milestones for work whose shape you do not yet know?
191. `[T]` "Tell me about a time you were the least experienced person in the room."
192. `[D]` How do you handle joining an organization whose domain you do not know?
193. `[D]` "Describe a time you had to learn something substantial fast in order to make a decision."
194. `[A]` What is your method for reducing ambiguity to a set of decidable questions, and where does it fail?
195. `[A]` How do you decide between exploring further and committing, and what signal ends the exploration?

---

## 13. Technical leadership decisions

> Assumed known: the technical depth lives in packs `01` to `11`. Here the question is how the decision was made, sold and lived with.

196. `[C]` "Walk me through the most consequential technical decision you have made."
197. `[D]` How do you tell a build-versus-buy story so that the reasoning is portable rather than specific?
198. `[D]` "Describe a migration you led." What must be in it beyond the technology?
199. `[T]` "Tell me about a time you chose the boring solution and were right - and one where you were wrong."
200. `[D]` How do you describe a decision whose payoff arrived after you left the team?
201. `[D]` "Tell me about deprecating something people were still using."
202. `[D]` How do you make the case for a rewrite, and how do you argue against one?
203. `[T]` "What is the worst architecture you have designed?"
204. `[D]` "Describe how you made a decision that locked the company into a vendor."
205. `[D]` How do you decide when a decision needs a document, a meeting, or neither?
206. `[D]` "Tell me about a time you reversed an architectural decision."
207. `[D]` How do you talk about a decision made by consensus without disappearing from it?
208. `[T]` "Tell me about adopting a technology that turned out to be a mistake."
209. `[D]` How do you evaluate a technology you have never used, in the time available?
210. `[A]` How do you decide what to standardize across teams and what to leave to team choice?
211. `[A]` Present the decision record you would write for a choice with a five-year lifetime.

---

## 14. Team, culture, distributed working and ethics

> Assumed known: your real context - onshore-offshore delivery, vendor and client-facing work at Sonata Software, and long-tenure platform work at Verizon India.

212. `[C]` "What kind of engineering culture do you want to work in?" Answer it without listing virtues.
213. `[D]` "Describe a team you improved." What is the evidence separate from the delivery numbers?
214. `[D]` How do you build trust with a team in a different time zone that you see for one hour a day?
215. `[T]` How do you talk about onshore-offshore dynamics honestly without either complaining or pretending it is frictionless?
216. `[D]` "Tell me about working with a client or vendor whose engineering standards were below yours."
217. `[D]` How do you handle knowledge concentrated in one person, and what have you actually done about it?
218. `[D]` "Describe how you have handled a teammate who was struggling personally."
219. `[D]` What do you do when a team's process is broken and everyone is used to it?
220. `[T]` "Tell me about a time you disagreed with your company's direction."
221. `[D]` How do you introduce a practice - code review standards, on-call, design docs - into a team that has never had one?
222. `[D]` "Describe a time you raised a concern nobody wanted to hear."
223. `[D]` How do you handle being asked to ship something you believe is unsafe, insecure or non-compliant?
224. `[T]` "Have you ever escalated over your manager's head?"
225. `[D]` How do you talk about a decision that was legal and profitable and that you were uncomfortable with?
226. `[D]` "Tell me about a time you had to enforce a rule you disagreed with."
227. `[D]` How do you handle credit - both giving it and not receiving it?
228. `[A]` Design the working agreement for a newly formed team split across two countries.
229. `[A]` What is the strongest argument against the way you prefer to work, and how do you accommodate it?

---

## 15. Career narrative and role fit

> Assumed known: your own history - Nittany Technologies 2007-2010, Verizon India 2010-2022, Sonata Software 2022-present, .NET from 2007, Java and Spring from 2016, AI engineering from 2024.

230. `[C]` Tell nineteen years as one line of reasoning rather than a chronology, in ninety seconds.
231. `[D]` "Why did you move from .NET to Java?" Make it a decision rather than a circumstance.
232. `[T]` Twelve years at one company. How do you present that as range rather than stagnation?
233. `[D]` "What did you do in the last two years that you could not have done five years ago?"
234. `[T]` Nineteen years and no manager title. How do you frame the principal track as a choice?
235. `[D]` "Why AI, and why in 2024?" Answer it so it does not sound like following a trend.
236. `[D]` How do you present depth in AI acquired over two years next to nineteen years of platform work?
237. `[D]` "What are you looking for in your next role?" Answer it in terms of the problem rather than the title.
238. `[T]` "Why are you leaving Sonata?" Answer without one negative word.
239. `[D]` "What is your biggest weakness?" - the version that works at principal level.
240. `[D]` "Where do you want to be in five years?" when the honest answer is "doing roughly this".
241. `[D]` How do you handle a gap, a short tenure or a role that did not go well?
242. `[T]` "You are overqualified for this." Answer it.
243. `[D]` "What would your last three managers say about you?" - including the criticism.
244. `[D]` "What is something you believe about software that most engineers you know disagree with?"
245. `[D]` How do you map your stories onto a published values framework - Amazon's leadership principles or an equivalent - without contorting them?
246. `[T]` The company's values include one you do not actually hold. What do you do?
247. `[D]` "What questions do you have for us?" - what does a principal candidate ask that a senior one does not?
248. `[D]` How do you assess whether the role is really at the level advertised, from inside the interview?
249. `[A]` Write the two-sentence positioning statement that should be in every interviewer's notes about you.
250. `[A]` If the loop concludes you are a strong senior rather than a principal, what evidence was missing, and what would you have done differently?
