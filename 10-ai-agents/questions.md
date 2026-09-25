# AI Agents Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java`, `03-microservices`, `07-devops`, `08-genai`, `09-rag` and `11-security` questions this material builds on. If those are shaky, go back before continuing.

This pack is about **the system built around the model**: the loop, the tools it can call, what it remembers, what it is allowed to do, how you stop it, how you know it worked, and what it costs. The model's own behavior is `08-genai`, retrieval as a capability the agent calls is `09-rag`, and distributed-systems fundamentals are `03-microservices`. Frameworks and provider APIs churn every quarter, so answer with the mechanism and treat any product name or number as an example rather than a commitment.

---

## 1. What an agent is, and when a workflow is the right answer

> Assumed known: `08-genai` Q80 (structured output and tool calling as a model capability) and `01-java` Q212-214 (RAG and orchestration basics).

1. `[C]` Define an agent in one sentence, and say precisely what distinguishes it from a chained LLM pipeline.
2. `[D]` Describe the autonomy ladder from a fixed prompt to a fully autonomous agent, with the control you give up at each rung.
3. `[T]` "We need an agent for this." Give the five questions that determine whether a deterministic workflow would be better, and the answers that disqualify the agent.
4. `[D]` What properties of a task make an agent the right architecture, and which properties predict expensive failure?
5. `[D]` Compare a workflow with LLM steps, a router, and an agent with a tool loop on cost, latency, debuggability and capability ceiling.
6. `[D]` Where does the nondeterminism in an agent actually come from? Enumerate the sources and say which you can remove.
7. `[T]` An agent demo works perfectly on ten tasks and fails on the eleventh in a way nobody can explain. What is structurally different about agents that makes this normal?
8. `[D]` What does "the agent decides" actually mean at the token level, and what does that imply about reliability?
9. `[D]` How do you decompose a business process into the part that should be code and the part that should be a model decision?
10. `[D]` What does an agent add to your failure surface that a request-response LLM feature does not have?
11. `[D]` Single agent with many tools versus a multi-step workflow with one model call per step. Give the decision criteria.
12. `[T]` Your agent achieves 85 percent task success. Is that shippable? Reason it through rather than answering yes or no.
13. `[A]` Set an "should we build an agent" checklist for teams in your organization, with the disqualifying answers.
14. `[A]` A stakeholder wants an agent that "just handles the whole process". Reframe that into something deliverable without losing their support.

---

## 2. The loop: control flow and termination

> Assumed known: Category 1 above and `08-genai` Q1-3 (autoregressive generation, the cost of prefill and decode).

15. `[C]` Draw the ReAct loop and name what is appended to the context on each iteration.
16. `[D]` ReAct versus plan-and-execute versus a state machine with model-selected transitions. Compare on controllability, latency and failure recovery.
17. `[D]` What exactly terminates an agent loop? Enumerate every termination condition a production agent needs.
18. `[T]` Your agent runs 40 iterations and stops only on the step cap. Give six causes and how you distinguish them.
19. `[D]` How does the context grow across iterations, and what does that do to cost, latency and quality?
20. `[D]` Context compaction inside a running loop: when do you do it, what do you keep, and what breaks when you get it wrong?
21. `[D]` What is the difference between the agent's *state* and the agent's *context*, and why does conflating them cause bugs?
22. `[D]` Parallel tool calls in one turn: what does the model emit, how do you execute them, and what ordering guarantees do you owe?
23. `[T]` The model calls the same tool with the same arguments three times in a row. What is happening and what do you do?
24. `[D]` How do you feed a tool error back into the loop so the model recovers rather than repeating the mistake?
25. `[D]` Streaming an agent run to a user: what do you show, what do you hide, and what changes about your architecture?
26. `[D]` Interrupting a running agent: what has to be true for that to be safe?
27. `[D]` Where does the system prompt end and the loop scaffolding begin? What belongs in each?
28. `[D]` How does prompt caching interact with an agent loop, and what breaks the cache on every iteration?
29. `[T]` Your agent is correct but takes 14 steps for something a human does in 3. Diagnose it.
30. `[A]` Design the loop for an agent that must complete a task within a hard 30-second budget, degrading rather than failing.

---

## 3. Tool design and contracts

> Assumed known: `01-java` Categories 1-3 (API design, exceptions) and `03-microservices` Q40-50 (service contracts, idempotency).

31. `[C]` What does the model actually see of a tool, and what does that imply about how you name and describe it?
32. `[D]` Design a tool schema well. Give the properties of a schema that a model uses correctly and one it does not.
33. `[D]` How many parameters is too many, and what do you do with a tool that genuinely needs fifteen?
34. `[T]` Your tool has an optional parameter with a sensible default and the model keeps setting it wrongly. Explain and fix.
35. `[D]` Enums, formats and constraints in a tool schema: what does the model respect, what does it ignore, and what must you validate?
36. `[D]` What should a tool return? Compare raw API output, a shaped summary and a structured result on token cost and model behavior.
37. `[D]` Tool errors: what does a good error message look like *to a model*, and how does that differ from one written for a human?
38. `[D]` Idempotency for agent tools: why does it matter more here than in ordinary service design, and how do you implement it?
39. `[T]` A tool succeeded but the response was lost before reaching the agent. Walk through what happens next and how you prevent double execution.
40. `[D]` Read tools versus write tools: what different guarantees, permissions and testing does each need?
41. `[D]` How do you keep a tool's output bounded when the underlying API can return 50,000 rows?
42. `[D]` Designing tools at the right granularity: one `manage_order` tool with a mode parameter, or six specific tools. Argue both, then decide.
43. `[D]` Versioning a tool contract when the agent's prompt and evaluation depend on its exact shape.
44. `[T]` You add a new tool and the agent's success rate on unrelated tasks drops. Explain the mechanisms.
45. `[D]` Long-running operations as tools: how do you model something that takes ten minutes?
46. `[A]` Design the tool contract standard for an organization where ten teams expose tools to a shared agent platform.

---

## 4. Tool selection at scale

> Assumed known: Category 3 above and `09-rag` Categories 5-8 (retrieval and reranking).

47. `[C]` What happens to selection accuracy as the number of tools grows, and why?
48. `[D]` What is the token cost of tool definitions, and at what point does it dominate your prompt?
49. `[D]` Tool retrieval: retrieve a relevant subset of tools per request. What is the mechanism, and what is the new failure mode?
50. `[T]` Your tool retriever returns the wrong tool set and the agent confidently uses the wrong tool. How do you make that recoverable?
51. `[D]` Hierarchical tool organization: namespaces, categories and a two-stage selection. What does it buy and what does it cost?
52. `[D]` How do you evaluate tool selection independently of task success?
53. `[D]` Two tools with overlapping purposes. What does the model do, and how do you fix it at the schema level?
54. `[D]` When should the agent not choose at all - when do you route deterministically instead?
55. `[D]` Few-shot examples for tool use: what do they fix, what do they cost, and when do they hurt?
56. `[T]` The model calls a tool that does not exist. What happened, and what are the layers of defense?
57. `[D]` Dynamic tool availability by user, tenant, permission or state. How do you implement it and what does it do to caching?
58. `[A]` Design tool discovery for an agent with access to 400 internal APIs.

---

## 5. Planning, decomposition and reflection

> Assumed known: Categories 1-2 above and `08-genai` Q60-70 (reasoning, chain of thought, test-time compute).

59. `[C]` What is the difference between planning and just running the loop, and when does an explicit plan earn its cost?
60. `[D]` Plan-then-execute versus interleaved planning. Compare on adaptability, cost, and recoverability from a bad plan.
61. `[D]` How do you represent a plan so that both the model and your code can operate on it?
62. `[T]` The agent produces a plausible plan whose third step is impossible. When do you find out, and how do you find out earlier?
63. `[D]` Replanning: what triggers it, how do you avoid thrashing, and what state carries over?
64. `[D]` Reflection and self-critique: what does the evidence actually support, and where does it fail?
65. `[D]` What is the difference between reflection, verification and validation in an agent, and which one do you trust?
66. `[D]` Decomposition depth: how do you stop an agent from decomposing a task into fifty trivial steps?
67. `[D]` Using a reasoning model for planning and a cheaper model for execution. What is the mechanism, and what breaks at the boundary?
68. `[T]` Adding a reflection step improved your benchmark and made production worse. Explain how.
69. `[D]` How do you give an agent a sense of progress so it knows whether it is getting closer to the goal?
70. `[D]` Backtracking: when a step fails irrecoverably, how does the agent get back to a good state?
71. `[D]` Where does a human-authored process fit relative to a model-generated plan?
72. `[A]` Design the planning layer for an agent handling multi-day workflows with human handoffs in the middle.

---

## 6. Memory and state

> Assumed known: `08-genai` Q24 (conversation compaction), `09-rag` Category 9 (context assembly) and `06-database` Categories 1-2.

73. `[C]` Name the kinds of memory an agent can have and say what each is actually for.
74. `[D]` Working memory versus the context window: what is the relationship, and why is "the context is the memory" a design smell?
75. `[D]` Design episodic memory: what gets written, when, and what is the retrieval key?
76. `[D]` Semantic memory - facts the agent has learned. How do you write it, how do you correct it, and who owns it?
77. `[T]` Your agent remembered something wrong and keeps repeating it. Walk through the whole lifecycle of that bug.
78. `[D]` Procedural memory: learned workflows and skills. What is the mechanism and what is the risk?
79. `[D]` What do you persist between sessions, and what must you deliberately forget?
80. `[D]` Memory retrieval is a retrieval problem. What is different about it from document retrieval?
81. `[D]` Summarization as memory compression: what is lost, and how do you tell when it matters?
82. `[D]` How do you version and migrate a memory store when its schema or the model changes?
83. `[T]` Two concurrent sessions for the same user write conflicting memories. What happens and how do you design around it?
84. `[D]` Memory and permissions: what happens when the agent remembers something the current user cannot see?
85. `[D]` How do you evaluate whether memory is actually helping?
86. `[D]` User-visible memory: what do you show, and what controls do you give?
87. `[D]` Scoping memory: per user, per session, per organization, per agent. What are the isolation implications of each?
88. `[A]` Design the memory architecture for an assistant used daily by 50,000 employees over years.

---

## 7. Multi-agent topologies

> Assumed known: `03-microservices` Categories 1-3 (service decomposition, communication, coupling) and Categories 1-5 above.

89. `[C]` Name the common multi-agent topologies and say what problem each was invented for.
90. `[T]` "We will use multi-agent to improve accuracy." Give the strongest argument for that, then the strongest argument against.
91. `[D]` Supervisor/orchestrator topology: how does control flow, and where does it break down?
92. `[D]` Handoff topology: what transfers between agents, and what is lost in the transfer?
93. `[D]` What is the actual cost of splitting one agent into three? Do the token and latency arithmetic.
94. `[D]` Context passing between agents: full transcript, summary or structured state. Compare.
95. `[D]` When does specialization genuinely help, and what is the evidence you would look for?
96. `[T]` Your multi-agent system produces worse results than a single agent with all the tools. Give five reasons.
97. `[D]` Error propagation across agents: how does one agent's mistake compound, and how do you contain it?
98. `[D]` Debate, voting and ensemble patterns: what do they buy, at what multiple of cost?
99. `[D]` How do you assign responsibility and ownership when a multi-agent run fails?
100. `[D]` Shared state between agents: what are the concurrency hazards, and what is the analogue in distributed systems?
101. `[D]` Deadlock, livelock and infinite handoff between agents. How do they arise and how do you prevent them?
102. `[D]` Testing a multi-agent system: what do you test in isolation and what only appears in composition?
103. `[D]` When is a "sub-agent" really just a tool, and why does that framing matter?
104. `[A]` Design a multi-agent system for a task where you have to defend the topology against "why not one agent".

---

## 8. Protocols and interop

> Assumed known: `03-microservices` Categories 2 and 8 (communication, service discovery) and `11-security` Category 4.

105. `[C]` What problem does MCP solve, and what does it not solve?
106. `[D]` Describe MCP's model: what a server exposes, how a client discovers it, and what the transport options are.
107. `[D]` MCP tools, resources and prompts. What is the distinction and when do you use each?
108. `[T]` You install a third-party MCP server. Enumerate everything you have just trusted it with.
109. `[D]` How do you handle authentication and per-user authorization through an MCP server?
110. `[D]` What breaks when an MCP server changes its tool schema, and how do you version it?
111. `[D]` Provider differences in function calling: what varies between vendors, and what should your abstraction hide?
112. `[D]` Agent-to-agent protocols: what does A2A-style interop actually require, and what is the hard part?
113. `[D]` When would you expose your service as an MCP server versus a plain REST API for agent consumption?
114. `[T]` Your MCP server is stateless but the agent assumes continuity. What goes wrong?
115. `[D]` Rate limiting, quotas and multi-tenancy for a tool server called by autonomous agents.
116. `[D]` Streaming, progress and cancellation over a tool protocol. Why does cancellation matter more here?
117. `[D]` Discovery and registry: how does an agent find out which servers and tools exist in your organization?
118. `[A]` Design the interop layer for a platform where internal teams and third parties both provide agent tools.

---

## 9. Environments: code execution, browsers and computers

> Assumed known: `07-devops` Categories 3-5 (containers, isolation) and `11-security` Categories 6-7.

119. `[C]` Why is code execution such a powerful agent capability, and what exactly are you accepting when you add it?
120. `[D]` Design a code execution sandbox: what are the isolation boundaries and what does each one stop?
121. `[D]` Filesystem, network and resource limits for an execution sandbox. What are the defaults and why?
122. `[T]` Your sandbox is a container with no network access. Give four ways an agent could still cause harm.
123. `[D]` Persistent versus ephemeral execution environments. What does statefulness buy and what does it cost?
124. `[D]` How do you return the output of code execution to the model without blowing the context?
125. `[D]` Browser automation as a tool: what does the agent actually perceive, and what are the failure modes?
126. `[D]` Computer use / screen-based agents: how does the loop differ, and why is reliability so much lower?
127. `[D]` Handling authentication in a browser agent without giving it credentials.
128. `[T]` A web page contains text instructing the agent to do something. What happens, and what stops it?
129. `[D]` Determinism and replay for environment interactions. What can you record and what cannot be replayed?
130. `[D]` Cost and latency of environment-based tools compared to API tools. When is the API worth building?
131. `[D]` Cleanup and lifecycle: how do you make sure an abandoned run does not leave a running sandbox?
132. `[A]` Design the execution environment tier for an agent platform serving many teams and untrusted generated code.

---

## 10. Human in the loop

> Assumed known: Categories 1-2 above and `04-system-design` Categories 9-10 (workflow, consistency).

133. `[C]` What kinds of human involvement exist in an agent system, and what is each one for?
134. `[D]` Which actions require approval? Give the criteria, not a list.
135. `[D]` Design the approval mechanism: what does the human see, what can they change, and what happens while they decide?
136. `[T]` Your approval rate is 99 percent. Is the approval step working? Reason it through.
137. `[D]` Interrupting and resuming a run around a human decision: what state must survive, and where does it live?
138. `[D]` Approval fatigue: how do you reduce the number of approvals without reducing safety?
139. `[D]` What does the human need in order to make a good decision in five seconds?
140. `[D]` Escalation to a human when the agent is stuck: what triggers it and what is handed over?
141. `[D]` Delegation and standing permissions: "always allow this for this user". How do you make that safe?
142. `[T]` A human approved an action based on a summary that misrepresented what the agent would do. Whose bug is this?
143. `[D]` Asynchronous approvals across hours or days. What does that do to the architecture?
144. `[D]` Auditing human decisions alongside agent decisions.
145. `[D]` How do you design the fallback when no human is available?
146. `[A]` Design human oversight for an agent that takes financial actions, with volume too high for per-action review.

---

## 11. Durability, checkpointing and workflow engines

> Assumed known: `03-microservices` Categories 4-6 (sagas, distributed data, resilience) and `07-devops` Category 6.

147. `[C]` Why does an agent run need durable state at all, and what breaks without it?
148. `[D]` What exactly do you checkpoint, and at what granularity?
149. `[D]` Resuming an interrupted run: what must be true for the resume to be correct rather than merely possible?
150. `[T]` You resume a run and it repeats a side effect. Explain the mechanism and the fix.
151. `[D]` Durable execution engines (Temporal, Step Functions and similar): what do they give an agent system, and what do they impose?
152. `[D]` Where does an agent framework's persistence end and a workflow engine begin? When do you need both?
153. `[D]` Event sourcing an agent run: what are the events, and what does replay give you?
154. `[D]` Deterministic replay when the model is nondeterministic. What is actually replayable?
155. `[D]` Long-running agents that live for days: what changes about deployment, versioning and state?
156. `[T]` You deploy a new prompt while 400 agent runs are mid-flight. What happens?
157. `[D]` Compensating actions and sagas for an agent that has performed partial work.
158. `[D]` Timeouts and deadlines across a durable agent run.
159. `[D]` Concurrency: two runs operating on the same entity. What are your options?
160. `[A]` Design durability for an agent platform where runs last from 2 seconds to 3 days.

---

## 12. Failure modes

> Assumed known: Categories 2, 5 and 11 above.

161. `[C]` Name the characteristic failure modes of agent systems and say which are unique to agents.
162. `[D]` Infinite and near-infinite loops: the mechanisms, the detection, and the controls.
163. `[T]` Your agent spent 400 dollars on one request. Walk through the causes and the controls that should have existed.
164. `[D]` Partial side effects: the agent did three of five steps and failed. What are the options and how do you choose?
165. `[D]` Cascading failure when a tool is degraded rather than down. Why is degraded worse for an agent?
166. `[D]` The agent gives up too early. What causes premature termination and how do you tune it?
167. `[D]` Hallucinated tool arguments and hallucinated tool results. How do you detect each?
168. `[T]` The agent reports success and did nothing. How is that possible, and how do you catch it?
169. `[D]` Context poisoning: one bad observation early in the run corrupts everything after it.
170. `[D]` Goal drift over a long run. What is the mechanism and what constrains it?
171. `[D]` Retry semantics in an agent: what is safe to retry, at which layer, and how many times?
172. `[D]` Model degradation or a provider incident mid-run. What is your behavior?
173. `[D]` How do you design so that the *worst* outcome of a failure is bounded?
174. `[D]` Rate limits and quota exhaustion in a fleet of agents. What is the systemic risk?
175. `[T]` Two agents in your fleet interact through shared state and produce an emergent failure nobody designed. How do you even find it?
176. `[A]` Build the failure taxonomy and control matrix you would present at an architecture review for an agent platform.

---

## 13. Agent security

> Assumed known: `11-security` Categories 1-4 and 12 (AI security), `09-rag` Q135 (injection through retrieval).

177. `[C]` What changes about prompt injection when the model has tools?
178. `[D]` Describe the confused deputy problem in an agent, with a concrete example.
179. `[D]` Least privilege for an agent: what is the unit of privilege, and how do you scope it?
180. `[T]` Your agent has read access to email and write access to a ticketing system. Construct the attack.
181. `[D]` Credential handling: how does an agent act on behalf of a user without holding their credentials?
182. `[D]` Token scoping and delegation: what does a correctly-scoped agent credential look like?
183. `[D]` The lethal trifecta - private data, untrusted content, external communication. Explain it and give the architectural response.
184. `[D]` Data exfiltration channels in an agent system. Enumerate them.
185. `[D]` Sandboxing untrusted tool output before it reaches the model.
186. `[T]` You add an "approve before sending" step. Which attacks does it stop and which does it not?
187. `[D]` Supply chain risk for tools, MCP servers and agent frameworks.
188. `[D]` Multi-tenant agent isolation: what must be separated and what commonly is not?
189. `[D]` Auditing an agent for a security review: what do you have to be able to show?
190. `[D]` Injection detection versus injection containment. Why is the second the real answer?
191. `[D]` What logging is required to investigate an agent security incident after the fact?
192. `[D]` Agent identity: how does a downstream system know which agent, acting for whom, made a call?
193. `[T]` A user asks the agent to do something they are authorized to do, in a way that produces an outcome policy forbids. Whose control fails?
194. `[A]` Design the security model for an agent with write access to production systems.

---

## 14. Evaluating agents

> Assumed known: `08-genai` Category 10 and `09-rag` Category 11 (evaluation discipline, judges, golden sets).

195. `[C]` What do you measure for an agent that you do not measure for a single LLM call?
196. `[D]` Task success rate: how do you define success for a task with several valid solutions?
197. `[D]` Trajectory evaluation: what is it, when does it beat outcome evaluation, and what does it cost?
198. `[T]` Your agent reached the right answer through a wrong process. Does that count as success?
199. `[D]` Building an agent evaluation set: what is in a case, and how many do you need?
200. `[D]` Simulating an environment for evaluation: what do you simulate, and where does simulation lie to you?
201. `[D]` Evaluating tool use specifically: the metrics and the failure modes they expose.
202. `[D]` Measuring efficiency: steps, tokens, wall clock, cost per successful task.
203. `[D]` Regression testing a nondeterministic system. How do you get a stable signal?
204. `[D]` LLM-as-judge for trajectories: how do you validate it, and what does it systematically miss?
205. `[T]` Your agent's success rate is 92 percent offline and 61 percent in production. Give six reasons.
206. `[D]` Evaluating the human-in-the-loop parts of the system.
207. `[D]` Online evaluation: what signals tell you an agent is failing in production?
208. `[D]` Pass@k versus pass^k for agents. What is the distinction and why does it matter commercially?
209. `[D]` What is your release gate for an agent change, and how does it differ from a prompt change gate?
210. `[A]` Design the evaluation platform for an agent product where each customer has different tools and data.

---

## 15. Observability and debugging

> Assumed known: `07-devops` Category 8 (observability), `09-rag` Q252 and Categories 11-12 above.

211. `[C]` What does a trace of an agent run need to contain to be useful?
212. `[D]` How do you model an agent run in OpenTelemetry terms - what are the spans and their attributes?
213. `[D]` A user says "it did the wrong thing yesterday". Walk from that sentence to the exact cause.
214. `[D]` Replaying a run: what do you record so that replay is faithful, and what remains unfaithful?
215. `[T]` The same input produces a different trajectory on every run. How do you debug anything?
216. `[D]` What metrics belong on an agent platform dashboard, and what does each one catch?
217. `[D]` Detecting a quality regression in production before users report it.
218. `[D]` Cost attribution: per run, per user, per tenant, per tool. Why does it matter operationally?
219. `[D]` Logging tool inputs and outputs safely when they contain customer data.
220. `[D]` Sampling: what do you keep at full fidelity and what do you sample?
221. `[D]` How do you make a trace legible to someone who did not build the agent?
222. `[D]` Alerting for agents: what are the signals, and what is the noise?
223. `[D]` Comparing two versions of an agent on the same production traffic.
224. `[A]` Design observability for an agent platform where you are on call for other teams' agents.

---

## 16. Cost, latency and concurrency

> Assumed known: `08-genai` Categories 13-14, `09-rag` Category 15 and `04-system-design` Category 12.

225. `[C]` Build the cost model for one agent run. What are the terms?
226. `[D]` Why is agent cost variance so much larger than a single-call feature's, and what does that do to capacity planning?
227. `[D]` The quadratic context problem in an agent loop: derive it and give three mitigations.
228. `[T]` Your average cost per run is acceptable and your p99 is ten times it. What do you do?
229. `[D]` Prompt caching in an agent loop: what is cacheable, and what invalidates it?
230. `[D]` Model routing within a run: cheap model for some steps, expensive for others. How do you decide per step?
231. `[D]` Where does latency go in an agent run, and what is the user-perceived latency?
232. `[D]` Parallelism inside a run and across runs. What are the limits of each?
233. `[D]` Budgets and quotas: per run, per user, per tenant, per day. How do you enforce them?
234. `[D]` Backpressure in an agent fleet: what happens when downstream tools cannot keep up?
235. `[D]` Concurrency model for a service running many long agent sessions in the JVM.
236. `[T]` You cut the step cap from 20 to 8 and cost dropped 60 percent with no measurable quality loss. What does that tell you?
237. `[D]` Batch and offline agents: what changes when there is no user waiting?
238. `[A]` Halve the cost of an agent platform with success rate held constant. Give the ordered plan.

---

## 17. The Java, Spring AI and AWS production path, design exercises and leadership

> Assumed known: `02-spring` Q237-246 (Spring AI), `05-aws` Categories 5-8 and everything above. The design questions are worked in full in [scenario-questions.md](scenario-questions.md); the leadership questions have no scripted answer.

239. `[C]` Design the module boundaries for an agent service in Java. What is behind a port and what is infrastructure?
240. `[D]` Spring AI's `ChatClient`, advisors and tool callbacks: what does the abstraction give you and where does it leak?
241. `[D]` How do you represent a tool in Java so that the schema, the validation and the implementation cannot drift apart?
242. `[D]` Where do you enforce authorization on a tool call in a Spring application, and why not in the tool method?
243. `[D]` Persisting agent state in Java: what is the schema, and what are the concurrency controls?
244. `[T]` Your agent service holds a thread per run and runs are 4 minutes long. What breaks and what do you change?
245. `[D]` Virtual threads, reactive or a workflow engine for agent execution. Justify by where the time goes.
246. `[D]` Testing an agent in Java: what do you fake, what do you record and replay, and what runs against the real model?
247. `[D]` Contract testing tools independently of the agent.
248. `[D]` Configuration as a release artifact for an agent: what is pinned together and why?
249. `[D]` Bulkheads, circuit breakers and fallbacks around tools, the model provider and the memory store.
250. `[D]` Deploying an agent service with in-flight runs. What is the strategy?
251. `[D]` Running agents on AWS: which compute model for which run duration, and what are the trade-offs?
252. `[D]` Step Functions as the agent loop versus an application-level loop. When is each right?
253. `[D]` Bedrock Agents and managed agent services: what do you give up and what do you get?
254. `[D]` Secrets, IAM roles and per-user credential scoping for agent tools on AWS.
255. `[T]` Your Lambda-based agent times out at 15 minutes on 3 percent of runs. Give the options and choose.
256. `[D]` Queueing, retries and dead letters for asynchronous agent runs on AWS.
257. `[D]` Cost controls on AWS for an agent platform: what is enforceable at the infrastructure layer?
258. `[D]` How does the retrieval service from `09-rag` appear to the agent, and what is the contract between them?
259. `[D]` Migrating from a framework-based agent to your own loop, or the reverse. What is the criterion?
260. `[A]` You inherit an agent service with a 900-line prompt, no step cap, no persistence and no evaluation. Sequence the remediation.
261. `[A]` Design a customer support agent that can read account data, issue refunds up to a limit and escalate, for 2 million customers.
262. `[A]` Design an internal engineering agent that triages alerts, investigates using observability tools and proposes remediation.
263. `[A]` Design a document-processing agent handling 200,000 documents a day with per-document human review below a confidence threshold.
264. `[A]` Design a coding agent operating on a large repository, from issue to reviewed pull request.
265. `[A]` Design a multi-tenant agent platform where 40 internal teams build agents on shared infrastructure.
266. `[A]` Design the safety, evaluation and rollout process for an agent that will take irreversible actions in production systems.
267. An agent or automation you took to production, with the autonomy level and how you chose it.
268. A time you argued against an agent and shipped something simpler.
269. An agent failure in production that you owned, and what changed afterwards.
270. A cost or reliability problem in an agentic system, with the before and after numbers.
271. How you built evaluation discipline for a nondeterministic system in a team that shipped on demos.
272. How you handled a stakeholder who wanted more autonomy than the system could safely support.
