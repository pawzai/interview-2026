# interview-2026

Interview preparation for a **Principal Engineer / Technical Lead / Solution Architect** move, covering Java, Spring, AWS, Security, AI and DevOps.

Context: 19 years of experience - .NET from 2007, Java and Spring Boot from 2016, AI engineering from 2024. Nittany Technologies (2007-2010), Verizon India (2010-2022), Sonata Software (2022-present).

---

## Packs

| Pack | Covers | Status |
| --- | --- | --- |
| [01-java](01-java/README.md) | Core Java, collections, concurrency, JVM, design, plus a broad first pass over Spring, security, data, microservices, AWS, DevOps and AI | 256 questions |
| [02-spring](02-spring/README.md) | Spring in depth - container internals, AOP, transactions, MVC and WebFlux, WebSocket and hypermedia, Spring Data including the non-relational stores, Security, Boot production engineering, Spring Cloud and Kubernetes, messaging endpoints, Spring Batch, testing, Spring AI and MCP, Boot 3 migration | 313 questions |
| [03-microservices](03-microservices/README.md) | Boundaries, contracts, event-driven architecture, distributed data, sagas, resilience, mesh, observability, decomposition, broker topology and legacy integration | 258 questions |
| [04-system-design](04-system-design/README.md) | Requirement framing and SLOs, estimation, component selection, caching and traffic tiers, consistency, sharding, reliability, multi-region, real-time fanout, AI in the request path, cost, plus 15 full design walkthroughs | 261 questions |
| [05-aws](05-aws/README.md) | Accounts and Organizations, workload identity, VPC and connectivity, edge and API entry, the Lambda execution model, compute selection, the event-driven backbone, event source mappings, Step Functions, data for serverless, S3, observability, quotas and failure modes, multi-region, IaC and delivery, cost engineering, Well-Architected | 270 questions |
| [05-aws/core-services](05-aws/core-services/README.md) | Breadth companion to 05-aws: EC2 and purchasing models, EBS and instance store, EFS and FSx, load balancing, Auto Scaling, Route 53, CloudFront and the edge, VPC at scale, RDS and Aurora operations, caching and analytics, containers, migration and transfer, operations and governance | 220 questions |
| [06-database](06-database/README.md) | Relational modeling, SQL, indexing, the optimizer, transactions and MVCC, storage, replication, sharding, caching and Redis, NoSQL, analytics, migrations, security and cost | 290 questions |
| [07-devops](07-devops/README.md) | Delivery pipelines and artifacts, trunk-based development, CI mechanics, supply chain and SLSA, containers, Kubernetes, GitOps and Argo CD, Terraform, progressive delivery, observability and SLOs, on-call and incident response, reliability, DevSecOps, FinOps, platform engineering | 270 questions |
| [08-genai](08-genai/README.md) | Transformer behavior, token and context arithmetic, decoding and determinism, model selection, prompting as engineering, structured output and tool interfaces, embeddings, context engineering, adaptation and fine-tuning, evaluation, hallucination and grounding, safety and prompt injection, inference and serving mechanics, cost and capacity, the Java and Spring production path, LLMOps | 278 questions |
| [09-rag](09-rag/README.md) | When retrieval is the right answer, ingestion and parsing, chunking, embeddings for retrieval, ANN index mechanics, lexical and hybrid search, query understanding and routing, reranking, context assembly, permission-aware retrieval, evaluation, grounding and abstention, freshness and re-embedding, graph and multi-hop and text-to-SQL, serving cost and latency, the Java and Spring AI path | 272 questions |
| [10-ai-agents](10-ai-agents/README.md) | When an agent beats a workflow, loop mechanics and termination, tool contracts and selection at scale, planning and reflection, memory, multi-agent topologies, MCP and A2A, sandboxes and computer use, human in the loop, durability and workflow engines, failure modes, agent security, evaluation and trajectories, observability, cost and concurrency, the Java and Spring AI and AWS path | 272 questions |
| [11-security](11-security/README.md) | Threat modeling and the secure SDLC, authentication, OAuth 2.1 and OIDC, authorization models, browser and session security, injection, API security, applied cryptography and TLS, secrets and KMS, Java and Spring Security, supply chain and CI/CD, container and Kubernetes, AWS security, AI and LLM security, detection and incident response, compliance | 300 questions |
| [12-behavioural](12-behavioural/README.md) | The nine leadership competencies and what evidence satisfies each, story construction and quantification, the story bank, ownership and influence, conflict and disagree-and-commit, failure and accountability, incident command, growing people, executive communication, prioritization, ambiguity, technical leadership decisions, culture and ethics, and the career narrative | 250 questions |
| [14-coding](14-coding/README.md) | Algorithm and data-structure patterns in Java, complexity as a design tool, concurrency exercises, in-process design-and-implement (LRU, limiter, queue, KV, ids, retry), refactoring, review and testing | 270 questions |
| [15-mock-interviews](15-mock-interviews/README.md) | How a loop is run and scored, the screen, every technical round type, coding and review rounds, behavioral and bar raiser, reverse interview and negotiation, plus six complete timed loops with interviewer scripts and rubrics | 222 questions |
| 13-architecture stories | Architecture narratives | Planned |

Start with [01-java](01-java/README.md) - it defines the answer frameworks (four-layer, CIDER, STAR-L) that every later pack reuses, and [02-spring](02-spring/README.md) treats its Spring material as prerequisite rather than repeating it. Finish with [15-mock-interviews](15-mock-interviews/README.md), which teaches no new technical material and instead rehearses delivering all of it under interview conditions.

## Pack structure

Every pack has the same five files plus a generated quiz page:

| File | Purpose |
| --- | --- |
| `README.md` | Roadmap, positioning, what interviewers probe |
| `questions.md` | Numbered, categorized questions with difficulty tags |
| `answers.md` | Mechanism-level model answers |
| `scenario-questions.md` | Production incidents, architecture exercises, leadership situations |
| `cheatsheet.md` | Fast revision reference |
| `quiz.html` | Interactive flashcard version, generated from the markdown |

`15-mock-interviews` adds one directory: [`mocks/`](15-mock-interviews/mocks/README.md), containing six complete timed interview loops and a printable scoring sheet.

## Regenerating the quiz pages

The markdown is the single source of truth. After editing `questions.md`, `answers.md` or `scenario-questions.md` in any pack:

```bash
python tools/build-quiz.py 02-spring   # one pack
python tools/build-quiz.py             # every pack
```

The output is a self-contained HTML file - no server, no internet connection, progress saved in the browser.
