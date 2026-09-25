# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Answers follow the four-layer structure defined in [../01-java/README.md](../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Hooks are written as *italic placeholders* - replace them with real detail from Verizon India and Sonata Software.

Unqualified statements about mechanism refer to **Kubernetes, GitHub Actions, Argo CD, Terraform and Prometheus**; other tools are named explicitly. Q261-265 are worked as full design exercises in [scenario-questions.md](scenario-questions.md). Q266-270 are story questions with no scripted answer.

---

## 1. Delivery pipeline design, versioning and artifacts

### Q1. CI, CD and continuous deployment

- **Continuous integration** - every developer merges to the mainline at least daily, and every merge is verified by an automated build and test run. The requirement is not a CI server; it is that branches are short-lived and that the team stops and fixes a red mainline.
- **Continuous delivery** - every build that passes is *deployable* to production, and the decision to ship is a business one, not an engineering one. The requirement is that the pipeline produces a releasable artifact and that no manual assembly step exists.
- **Continuous deployment** - every build that passes *is* deployed. The requirement is automated verification you trust enough to remove the human, plus fast automated rollback.

The distinction interviewers want is the last one: continuous delivery is a property of the artifact, continuous deployment is a property of the pipeline. Most organizations that claim continuous deployment have continuous delivery with a rubber stamp, and most that claim continuous delivery cannot actually ship the current mainline commit today.

### Q2. Stage sequence for a Java microservice

Ordered by cost of feedback, cheapest first:

1. **Pre-merge, seconds** - format, lint, compile, unit tests, secret scan. This is the gate on the pull request.
2. **Build and package once** - the versioned JAR and the container image, digest recorded. Everything downstream references this digest.
3. **In parallel** - integration tests against Testcontainers, contract tests, SAST, SCA, image scan, SBOM generation and signing. These do not depend on each other, so serializing them is pure latency.
4. **Deploy to a shared pre-production environment** and run the smoke suite and any end-to-end tests that genuinely need a deployed system.
5. **Gate: promote** - the artifact is tagged for production. No rebuild.
6. **Progressive production rollout** with automated analysis and rollback.

What is a **gate**: compile, unit tests, secret scan, signature verification, policy checks on the deployment manifest. What is **advisory**: coverage deltas, most lint categories, informational CVEs with no reachable path. The mistake is making everything a gate, which trains the team to bypass gates.

*Hook: a pipeline where you moved a stage from a gate to advisory and what happened to throughput.*

### Q3. A green 55-minute pipeline `[T]`

The inconvenience is not the problem; the problem is what a 55-minute pipeline does to behavior.

- Developers **batch changes** to avoid paying the cost, so each change is bigger, riskier and harder to bisect.
- They **context-switch** away and come back an hour later, so the cost of a failure is a full re-orientation rather than a fix.
- **Merge queues back up**, so integration happens less often, which is the exact thing CI exists to prevent.
- **Rollback and hotfix are gated by the same 55 minutes**, so your MTTR has a hard floor you cannot beat during an incident.

So a 55-minute pipeline is a reliability defect, not an ergonomics one. I would treat the pipeline's own p50 and p95 as an SLO with a target - ten minutes to a merge decision - and attack the critical path: parallelize, cache correctly, split the affected set, and move anything that is not a merge gate to a post-merge or nightly run.

### Q4. Build once, deploy many

**Identical**: the artifact bytes. The same image digest - not the same tag - runs in staging and production. The application code, the dependency set, the base image, the JVM version and the build-time configuration are all fixed at build time and never re-resolved.

**Allowed to differ**: everything injected at start-up. Endpoints and connection strings, credentials, resource requests and limits, replica counts, log level, feature flag defaults, and the observability endpoints. These live in the deployment manifest and the secret store, not in the artifact.

The boundary case is anything the framework resolves at build time. Spring profiles are fine because they select at start-up; a `@ConditionalOnProperty` bean that is *compiled out* is not. GraalVM native images move a lot across this line, which is one of their real costs.

### Q5. Rebuilding per environment `[T]`

1. **You test a different artifact than you ship.** Dependency resolution is not deterministic unless you have forced it to be. A transitive version, a base image tag, or a plugin resolves differently on Tuesday than it did on Monday, so the staging sign-off applies to bytes that no longer exist.
2. **The production build is the least-tested build.** It is the only one that has never run anywhere before it runs in production, which inverts the entire point of a pipeline.
3. **Rollback is not a rollback.** To go back you rebuild the old commit, and you may not get the old artifact - the base image tag moved, a dependency was yanked, the build environment changed. During an incident this is the worst possible time to discover it.

There is a fourth, quieter one: the build becomes a place people hide configuration, so you can no longer answer "what is running in production" from the manifest alone.

### Q6. Versioning schemes

| | Library | Service image |
| --- | --- | --- |
| Scheme | Semantic versioning | Commit SHA (or SHA plus a readable prefix) |
| Consumed by | Other builds, at compile time | A deployment manifest, at runtime |
| Question it must answer | "Is this safe to upgrade to?" | "Exactly what code is running?" |

A library has *consumers who must reason about compatibility*, and semver is a compatibility contract - it communicates intent about breaking changes, and tooling can act on it. A service image has exactly one consumer, the deployment manifest, and the only question that ever matters at 3 am is which commit produced it. Semver on a service image is theater: nobody chooses to "upgrade" to it, and the major-version bump communicates nothing to anyone.

Calendar versioning is a reasonable middle for things released on a cadence rather than by compatibility - a platform bundle, a base image, an internal distribution - where "how old is this" is the important question. I typically tag service images with both the immutable SHA and a moving human-readable tag for convenience, while everything automated references the digest.

### Q7. Immutable artifacts

An immutable artifact is one whose content cannot change after publication, and whose identifier is derived from that content. For an OCI image the digest (`sha256:...`) is that identifier - it is the hash of the manifest, so it cannot point at different content.

Tags are mutable pointers. Even a "release" tag can be overwritten by anyone with push rights, and the resulting incident - production silently running different bytes than the pipeline verified - is invisible in the manifest. Enforcement, in layers:

1. **Registry immutable tags** - ECR tag immutability, Artifactory or Nexus release-repo immutability. Turn it on; it is one setting.
2. **Reference by digest in the deployment manifest.** This is the control that actually works, because it is independent of what the registry allows.
3. **Verify at admission** - signature and digest verification in the cluster, so an unexpected image cannot run even if it was pushed.
4. **Immutable git tags** and a protected release branch, so the source side is not the loophole.

The trade-off is ergonomics: digests are unreadable, so the pipeline has to write them into the manifest rather than a human doing it.

### Q8. Snapshot versus release artifacts

A Maven `-SNAPSHOT` version is explicitly mutable: the coordinate resolves to whatever timestamped build the repository currently holds, and Maven re-resolves it on a schedule. A release version is resolved once and cached forever.

What breaks when a snapshot reaches production is that the artifact is no longer identified. Two builds of the "same" version differ; you cannot reproduce the deployed bytes; and rollback to "the previous version" is undefined. It also means a downstream team's build result depends on when they built.

Prevention is a pipeline check, not a convention: fail the release build if any resolved dependency has a `-SNAPSHOT` version, forbid the snapshot repository in the release profile entirely, and configure the artifact repository so the release repo will not accept a snapshot coordinate. The Maven Enforcer plugin's `requireReleaseDeps` rule does the first one in three lines.

### Q9. Artifact promotion

Promotion moves an *identity* through environments, not bytes through builds.

1. The build publishes the image once, to a single registry path, addressed by digest. It is also signed, and an SBOM and provenance attestation are attached to the same digest.
2. Environment membership is recorded outside the artifact. Two common mechanisms: an immutable annotation or tag applied to the digest (`env/staging`, `env/prod`), or - the GitOps version - a commit to the environment's manifest directory that sets `image: repo@sha256:...`.
3. The deployment manifest in each environment references the digest. Promoting to production is a pull request that changes one line in the production overlay, which makes the promotion reviewable, auditable and revertable by the same mechanism as code.
4. Verification at each boundary: signature valid, provenance says the digest came from the expected repository and workflow, policy checks pass.

The property this gives you is that "what is in production" and "what was tested" are the same question with the same answer, and the answer is a hash.

### Q10. Retention and garbage collection

Policy I would set:

| Artifact class | Retention |
| --- | --- |
| Untagged image layers and dangling manifests | 7 days |
| Feature-branch and pull-request images | 14 days, or delete on branch deletion |
| Mainline builds not promoted | 30-90 days |
| Anything ever deployed to production | Retain until it has been superseded for the full rollback window, then archive |
| Release artifacts of published libraries | Never delete |
| SBOMs, provenance and signatures | For the compliance retention period, independent of the image |

Two rules do most of the work. **Never delete something that is currently referenced by a live manifest** - garbage collection must read the cluster or the GitOps repo, not just a date. And **never delete a published library version**, because you break every consumer's reproducible build and you cannot undo it.

The cost driver people miss is that layers are shared, so deleting 90 percent of your tags may free almost nothing; you have to garbage-collect unreferenced blobs to see any saving.

### Q11. Pipeline as code

Beyond reviewability, four things:

1. **The pipeline is versioned with the code it builds.** A commit from eight months ago builds with the pipeline definition from eight months ago, which is the only way a build is reproducible at all.
2. **It is testable and reusable.** You can extract a shared workflow, version it, and roll it out gradually. A UI configuration can only be copied.
3. **It is the audit evidence.** Who changed the deploy step, when, and who approved it - answered by git history rather than by a screenshot of a settings page.
4. **It removes a class of privileged mutable state.** A UI-configured pipeline is a production system that anyone with console access can silently change, usually with credentials attached.

The trade-off is real: YAML is a poor programming language, the feedback loop on a pipeline change is slow, and complex pipeline logic in YAML becomes unreadable. My rule is that the pipeline definition should orchestrate and delegate - anything with logic goes into a script or a small tool that can be run and tested locally.

### Q12. Reproducible builds `[T]`

A containerized build fixes the *operating system and the tools*. It does not fix:

- **Dependency resolution.** A version range, a snapshot, or an unpinned plugin resolves against the network at build time. Yesterday's resolution is not today's.
- **Base image tags.** `FROM eclipse-temurin:21-jre` is a moving pointer; the digest under it changes.
- **Network-fetched anything** during the build - a downloaded binary, a `curl | sh`, a remote schema.
- **Non-determinism inside the build** - timestamps, file ordering from the filesystem, embedded build metadata, random test ordering.
- **Build-time environment injection** - a variable present on the developer's machine but not on the runner, or the reverse.

Reproducibility requires: pin the base image by digest, pin every dependency and plugin (lock file or explicit versions), forbid network access outside the resolved dependency set, and normalize timestamps and file ordering in the archive. Then verify it - build twice on different machines and compare digests. Nobody discovers a reproducibility break by reasoning about it.

### Q13. Ordering for the first three minutes

The developer should learn *the most likely failure* first, and the ordering follows the base rate of what actually breaks:

1. **Seconds** - format and lint, so trivially wrong things never consume a runner.
2. **Under a minute** - compile. A compile error should never be discovered at minute forty.
3. **One to three minutes** - the unit test suite, parallelized, plus secret scanning. This is where most real defects surface.
4. **Then** everything slow and everything requiring infrastructure.

Two techniques matter. **Fail fast within a stage**: stop the job on first failure for cheap stages, but run the full set for the test stage - a developer wants all failing tests, not the first one. And **run the tests most likely to fail first**: test-impact ordering by recent failure history and by proximity to the changed files gets most of the benefit of full parallelization for none of the cost.

The anti-pattern is a long serial security or quality stage in front of the tests, which trains everyone to ignore it.

### Q14. DORA metrics and how to instrument them

- **Deployment frequency** - count of successful production deployments per service per period. Source: the deployment event, from the CD system or from the GitOps repo's commit history to the production overlay.
- **Lead time for change** - time from first commit on the change to that commit running in production. Source: join the commit timestamp to the deployment event by SHA. This is why deployments must record the SHA.
- **Change failure rate** - proportion of deployments that cause a degraded service requiring remediation. Source: incidents linked to a deployment, plus automatic rollbacks. This one requires a human definition; the others do not.
- **MTTR** - time from the start of degradation to restoration. Source: the incident record, not the ticket close time.

Everything except change failure rate is derivable from two data you already have: deployment events tagged with the SHA, and the git history. I would emit a deployment event as a first-class metric from the CD system rather than reconstructing it later, because reconstruction is where these programs die.

### Q15. 2 percent change failure rate and terrifying releases `[T]`

The missing metric is **the cost of a failure**, not its frequency. A 2 percent change failure rate with a 4-hour recovery and customer-visible data damage is far worse than 15 percent with a 90-second automated rollback. Fear is a rational response to unbounded downside, and DORA's four metrics do not measure downside.

There is usually a second thing hiding: the 2 percent is measured on *deployments*, and if the team batches a fortnight of changes into one deployment, the per-change risk is invisible. Terror plus a good number almost always means large, infrequent, hard-to-reverse changes.

What I would measure instead, or in addition:

- **Time to rollback**, actually measured by exercising it, not estimated.
- **Change size** - commits, files or lines per deployment - as a leading indicator.
- **Proportion of deploys that are reversible without data intervention.** This is the one that maps to fear.
- **A developer confidence survey**, which sounds soft and is the most predictive signal in the list.

*Hook: a team whose metrics looked good and whose releases were feared, and what you changed.*

### Q16. Three teams, three pipelines `[A]`

I do not standardize the pipelines. I standardize the **interfaces and the guarantees**, then make the standard implementation so obviously easier that adoption is a choice.

Sequence:

1. **Find out why they differ.** Some of the divergence is accidental and some encodes a real constraint - a regulated workload, a different runtime, a genuinely different test topology. Standardizing over a real constraint is how you get a mandate everyone routes around.
2. **Agree the contract, not the steps.** Every pipeline must produce a signed image addressed by digest, an SBOM, a deployment event with the SHA, and must pass the same policy checks. How it gets there is the team's business.
3. **Build the paved road as a versioned reusable workflow**, and migrate the most willing team first. Their result is the argument.
4. **Enforce only the contract, at the boundary** - admission control on unsigned images, a required check on the deployment event. This is enforcement that does not care how the pipeline is written.
5. **Retire the divergence opportunistically**, when a team is already touching their pipeline. Never as a project.

The failure mode to avoid is a platform team that takes ownership of three pipelines it does not understand and becomes a ticket queue in front of everyone's delivery. Standardization that removes team autonomy without removing team responsibility is worse than the divergence.

*Hook: a standardization effort you led, and the exception you agreed to.*

---

## 2. Source control, branching and trunk-based development

### Q17. GitFlow, GitHub Flow and trunk-based development

| | Branch lifetime | Conflict surface | Release cadence |
| --- | --- | --- | --- |
| GitFlow | Weeks; `develop`, `release/*`, `hotfix/*`, `feature/*` | Large - long-lived parallel lines that must be merged back both ways | Scheduled, batched |
| GitHub Flow | Days; short branch off `main`, PR, merge, deploy | Moderate | On merge |
| Trunk-based | Hours; commit straight to `main` or a branch measured in hours | Minimal - everyone integrates against the same tip continuously | Continuous, decoupled from merge via flags |

GitFlow was designed for versioned, downloadable software with multiple supported versions in the field. That is a real problem and GitFlow solves it. For a continuously deployed service there is exactly one version in the field, so the `develop`/`release` machinery is pure cost - it creates the integration debt it then spends effort merging.

The single most useful framing in an interview: branching strategy is a **deferral policy for integration pain**. GitFlow defers it to a release branch merge, trunk-based refuses to defer it at all, and deferred integration pain compounds.

### Q18. Preconditions for trunk-based development

Not the practice - the preconditions:

1. **A test suite fast and trustworthy enough to gate a merge.** If the suite takes 40 minutes or is flaky, developers will not commit small and often.
2. **A mechanism to hide incomplete work** - feature flags, or branch-by-abstraction for structural change. Without it, "commit daily" means "ship half a feature".
3. **A culture that stops for a red mainline.** Trunk-based with a mainline that is red for hours is strictly worse than branches.
4. **Small changes as a norm**, which usually means the team has learned to decompose work, which is a skill and not a policy.
5. **Fast, safe rollback**, because trunk-based increases deployment frequency and therefore the number of opportunities to be wrong.
6. **Code review that happens in hours, not days.** A two-day review latency forces long-lived branches no matter what the policy says.

If you list these rather than "everyone commits to main", you have answered the question the interviewer is actually asking, which is whether you have done it or read about it.

### Q19. "Our features take three weeks" `[T]`

The real constraint is not the feature size; it is that the team has no way to integrate incomplete work safely. Three weeks of work is not three weeks of un-integrable work - it is thirty commits, of which twenty-eight are refactoring, plumbing, schema, tests and scaffolding that could all be on the mainline behind a flag.

What I propose, concretely:

1. **Branch by abstraction** for structural change: introduce the seam, move callers to it one at a time on the mainline, then implement behind it. Every step is shippable.
2. **A release flag** for the user-visible part, defaulted off, removed as soon as the feature is on.
3. **Expand-contract for the schema**, so data structure changes land ahead of the code that uses them.
4. **Split the work in the plan, not in the branch.** If a story cannot be decomposed into daily increments, that is usually a story-writing problem, and it will also be a review problem and an estimation problem.

I would also be honest about the case where a branch is still right - a genuinely exploratory spike, or a fork-scale rewrite - which is Q20.

### Q20. Feature branches versus feature flags

| | Long-lived branch | Feature flag |
| --- | --- | --- |
| Cost | Merge conflicts growing super-linearly with lifetime; the code is untested against the current mainline until the end | Conditional complexity in the code, a combinatorial test surface, and flags that outlive their purpose |
| Failure mode | A painful, risky, all-at-once merge | A permanent thicket of dead conditionals nobody dares remove |
| Reversibility | Revert the merge - large, coarse | Flip the flag - instant, targeted |

The flag's cost is *ongoing and manageable*; the branch's cost is *deferred and compounding*. That asymmetry is why flags are the default.

A branch is still correct when: the change is genuinely exploratory and may be discarded; the change is so structurally invasive that the flag would have to wrap half the codebase; or the work is by an external party or on a fork you do not control. In the invasive case the honest answer is often that the change should be sequenced differently rather than isolated.

### Q21. Merge, squash and rebase

| | History shape | Bisect | Revert | Blame |
| --- | --- | --- | --- | --- |
| Merge commit | Non-linear, preserves every branch commit | Works, but lands you on intermediate commits that may not build | `git revert -m 1` on the merge - clean | Points at the original small commit - most useful |
| Squash | Linear, one commit per PR | Best case: every commit on the mainline is a complete, building change | Revert one commit - cleanest | Points at the squashed commit - coarser, loses intermediate authorship |
| Rebase | Linear, preserves individual commits | Works well if the branch commits each build; unreliable if they do not | Multiple reverts, or a range revert | Fine-grained, but the commits were never tested in this order |

My default is **squash for feature PRs** and merge commits only for long-running integration branches. Squash gives you the property that matters most operationally - every commit on `main` is a deployable unit, so bisect and revert both operate on the same granularity as deployment. The cost is that you lose the intermediate history, which is a real loss for a large refactor; there I ask for a rebase merge with commits that each build.

Rebasing a *shared* branch is the thing to warn about: it rewrites commits other people have based work on.

### Q22. Reverting a bad production change

For a shared branch: **`git revert`**, always. `git reset` rewrites history that other people have pulled, which turns one broken deploy into a broken repository for the whole team.

But the more important part of the answer is that the git operation is rarely the fastest path. Order of preference during an incident:

1. **Redeploy the previous artifact.** The image already exists, it is already verified, and it takes as long as a rollout. No build, no review, no merge.
2. **Flip the feature flag**, if the change was behind one. Seconds.
3. **`git revert` and roll forward**, which is what you do once the bleeding has stopped, so that the mainline reflects reality and nobody redeploys the bad commit tomorrow.

A forward fix is right when rollback is impossible - a migration has run, an event has been published, an external system has been called - or when the revert would itself be large and risky. The judgement is about *which action has the smaller and better-understood blast radius*, not about which is philosophically purer.

*Hook: a rollback where redeploying the previous image beat the revert by twenty minutes.*

### Q23. Finding a regression in 300 commits

`git bisect` performs a binary search over the commit range: you mark a known-good and a known-bad commit, git checks out the midpoint, you test and mark it, and roughly `log2(n)` iterations later - about 8 or 9 for 300 commits - you have the first bad commit. `git bisect run <script>` automates the whole thing if you can express the test as an exit code, which is the version worth doing.

What makes it fail:

- **Commits that do not build.** Bisect lands on an intermediate commit from a rebase-merged branch that was never independently tested. `git bisect skip` handles a few; a history full of them defeats it. This is a strong argument for squash merges.
- **A non-deterministic or flaky reproduction.** Binary search over a noisy oracle converges on nonsense. Get a deterministic reproduction first, even if it takes longer than the bisect would.
- **The bug is not in the code.** A dependency version, a config change, an environment change, or data. Bisect will confidently blame a commit that merely exposed it.
- **A first-parent-only history** where the actual change is inside a merged branch; `--first-parent` finds the merge, and you then bisect within it.

### Q24. Monorepo versus polyrepo

| | Monorepo | Polyrepo |
| --- | --- | --- |
| Dependency management | One version of everything; upgrade the shared library once and fix all callers in the same commit | Version-and-publish; N teams upgrade on their own schedule, so N versions are live |
| CI cost | High by default; requires a build graph and change detection to be viable | Naturally scoped; each repo builds itself |
| Atomic cross-service change | Possible - one commit, one review, one revert | Impossible; you need a coordinated multi-repo sequence |
| Release independence | Requires deliberate discipline; the repo does not enforce it | Enforced by structure |
| Discoverability and refactoring | Excellent - global search and global rename | Poor |
| Access control | Coarse; path-based controls are bolted on | Natural per-repo boundaries |

The honest summary: a monorepo trades tooling investment for coordination cost, and a polyrepo trades coordination cost for version sprawl. Both work at scale, both fail without investment, and the deciding factor is usually which failure your organization is better equipped to absorb.

### Q25. 90-minute monorepo CI `[T]`

The fix is not more machines; it is that the repository is being treated as one build target when it is a **graph of targets**. More machines makes the wrong build faster and doubles the bill.

What that means concretely:

1. **Model the dependency graph explicitly** - Bazel, Gradle's project graph, Nx, Turborepo, or a hand-maintained module manifest. The graph must include test-only and config dependencies, not just compile dependencies.
2. **Compute the affected set** from the diff by walking the graph transitively upward from the changed nodes. Only those targets build and test.
3. **Cache by content hash.** A target whose input hash is unchanged does not rebuild - it restores from cache. On a mature setup most of a build is cache hits, and that is where the order-of-magnitude win is, not in parallelism.
4. **Share the cache remotely** so the first developer to build a target pays and everyone else, including CI, does not.
5. **Then** parallelize what remains across the graph's independent branches.

The residual risk is that the graph is wrong - see Q42. That is a correctness problem you manage with a periodic full build on the mainline, not something you pretend away.

### Q26. Branch protection minimum set

On the default branch:

- **Required status checks**, and specifically the checks that must be *up to date with the branch tip*, otherwise two individually-passing PRs merge into a broken mainline (the semantic conflict - use a merge queue for this).
- **Required review** - at least one, from someone other than the author. Code-owner review for anything in the pipeline, the deployment manifests or the security-relevant paths.
- **Dismiss stale approvals on new commits**, or the review means nothing.
- **Linear history** if you squash-merge, which keeps bisect and revert honest.
- **No force push, no deletion.**
- **Signed commits** where the compliance posture requires provenance back to a human identity; verified is better than unverified but this is the one I would trade first if it is causing friction.

**Bypass**: nobody routinely, including administrators. If you allow an emergency bypass, it must be logged, alerted on, and reviewed after the fact - a break-glass path that produces evidence. The rule I actually enforce is that automation identities never bypass, because that is where a bypass becomes invisible.

### Q27. Conventional commits and automated release notes

Beyond tidy history, conventional commits make the *intent* of a change machine-readable, and that unlocks pipeline behavior:

- **Automatic semantic version calculation** for libraries: `fix:` bumps patch, `feat:` bumps minor, `BREAKING CHANGE:` bumps major. The version stops being a human judgement that someone forgets.
- **Generated changelogs and release notes**, grouped by type, which matters most for a shared platform library with 40 consumers.
- **Routing decisions**: a `chore(deps):` commit can take a lighter pipeline; a `feat:` touching a public API can require an extra review.
- **Correlation in incident review**: filtering deployment events by commit type when reconstructing a timeline.

The trade-off is that it only works if it is enforced (commitlint on the PR title, since squash merges make the PR title the commit message) and that enforcement on individual commits inside a branch is friction people resent. Enforce it at the PR title, where it maps one-to-one with the squashed commit.

### Q28. Shared libraries across 30 services

| Approach | Verdict |
| --- | --- |
| **Versioned artifact** | Default. Consumers upgrade on their own schedule, the version is an explicit compatibility statement, and the build is reproducible. Cost: N versions live simultaneously, and coordinated upgrades are a campaign. |
| **Copy** | Legitimate for small, stable, rarely-changed code where the coupling cost of a shared library exceeds the duplication cost - a 40-line utility. Fails badly for anything with a security surface, because you now have 30 places to patch. |
| **Git submodule** | Almost never. It gives you the coupling of a shared library with the versioning ergonomics of a copy, plus a tooling experience that every team gets wrong at least once. |

For a 30-service estate my policy is: a small number of well-owned versioned libraries with a published support window (current and previous minor supported, older versions get security fixes for a defined period), automated upgrade PRs so the upgrade cost per consumer is a review rather than a project, and a hard rule that the shared library never contains business logic - only cross-cutting plumbing. Business logic in a shared library is a distributed monolith with extra steps.

### Q29. Shared library breaks eleven services a week later `[T]`

The process failure is that **the blast radius of the library change was never measured before it was published, and the upgrade was invisible after it was**.

Specifically:

1. **The transitive bump was not surfaced.** The library's release notes said "internal refactor"; the actual change was a dependency's major version reaching every consumer's classpath.
2. **Nothing tested the consumers.** A shared library used by 30 services needs consumer-side verification - either contract tests the library runs against, or an automated build of the top consumers before release.
3. **The upgrade was silent.** If automated dependency PRs merged it without a canary, eleven services shipped a transitive change with no deployment-time signal attached to it.
4. **A week's delay means it was not deployment-correlated.** The failure surfaced on a code path exercised weekly, which means the integration tests do not cover the path and the rollout had no soak period.

The fixes: publish the resolved dependency diff in the library's release notes; run a consumer verification build for the top N services on every library release; require dependency-update PRs for platform libraries to go through the same canary as a code change; and use a BOM or dependency-management block so a transitive bump is an explicit, reviewable decision rather than a resolution side effect.

*Hook: a transitive dependency change that reached production silently.*

### Q30. Monorepo for 40 engineers and 25 services `[A]`

**For.** At 25 services and 40 engineers, cross-service change is frequent and coordination cost is the dominant tax. A monorepo makes a shared-library upgrade one commit instead of 25 PRs; makes a global refactor mechanically possible; gives every engineer a searchable view of the estate, which matters enormously for onboarding at this size; and removes the "which version of the platform library is service X on" question entirely.

**Against.** It requires real tooling investment - a build graph, remote caching, change detection - before it is even neutral, and that investment competes with product work. It weakens the boundary that keeps services independently deployable, so you get a distributed monolith unless you enforce the boundary another way. Access control is coarse. And it is close to irreversible: splitting a monorepo later is far harder than merging repositories.

**Recommendation.** For a 40-engineer estate that is *already* polyrepo and functioning, I would not migrate. The coordination pain at 25 services is real but manageable with a good BOM, automated dependency PRs and a consumer verification build, and that costs a fraction of the monorepo tooling investment.

I would change my mind if: cross-service changes were routinely spanning three or more repositories; the estate were growing toward 60+ services with the same team size; the organization already had monorepo tooling and expertise from elsewhere; or we were greenfield, where the migration cost is zero and the decision is nearly free.

The version I would actually push for either way is a **middle path**: group repositories by bounded context so a coherent change is usually within one repository, which captures most of the atomicity benefit without the tooling bill.

*Hook: a cross-repository change that took a week and would have been one commit.*

---

## 3. CI mechanics - runners, caching, matrices and monorepo pipelines

### Q31. GitHub Actions execution model

1. An **event** occurs - a push, a pull request, a schedule, a manual dispatch, or an API call.
2. GitHub evaluates every **workflow** in `.github/workflows` on the relevant ref whose `on:` matches, and whose top-level conditions pass.
3. Each workflow contains **jobs**. Jobs run in parallel by default and are ordered by `needs:`. Each job is assigned a **runner** - a fresh VM or container for hosted runners.
4. The job runs its **steps** sequentially in the same filesystem and the same shell environment. A step is either a `run` command or a `uses` action.
5. Artifacts and outputs are the only sanctioned way to pass data between jobs.

**Isolation begins at the job.** Each job gets its own runner, its own filesystem, its own `GITHUB_TOKEN` with its own permissions, and its own secret set. **It ends at the step**: steps within a job share everything - environment, filesystem, network, credentials - so a compromised third-party action in step 3 sees what step 5 was going to do.

This is the single most useful thing to know for the security questions later: the security boundary is the job, so anything requiring elevated credentials should be its own job with its own narrowly-scoped permissions.

### Q32. Hosted versus self-hosted runners

| | GitHub-hosted | Self-hosted |
| --- | --- | --- |
| Cost | Per-minute, expensive at scale, zero fixed cost | Infrastructure cost plus operational ownership; much cheaper per minute at volume |
| Security | Fresh VM per job, discarded after; GitHub's problem | Yours; state persists unless you make it ephemeral |
| Network access | Public internet only, unless you pay for a network path | Direct access to VPC resources - databases, private registries, internal services |
| Cold start | Seconds, but no warm caches, no warm Docker layer cache | Can be warm, which is the biggest single build-time win for Java |
| Hardware | Fixed sizes | Whatever you want - more cores, more memory, ARM, GPU |

I run self-hosted when: builds need private network access (integration tests against a real internal dependency); the volume makes per-minute pricing indefensible; the build is heavy enough that warm caches change the shape of the pipeline; or compliance requires the build to run inside our own boundary.

I stay hosted for public-facing repositories, anything triggered by untrusted contributors, and low-volume repositories where the operational cost of running the fleet exceeds the savings.

The honest trade-off is that self-hosted runners are a production system with production credentials that most organizations operate as if it were a build box.

### Q33. Reused self-hosted runner leaks `[T]`

1. **Filesystem residue.** The previous job's checkout, build outputs, temporary files and any credentials written to disk - a `~/.docker/config.json`, a `~/.m2/settings.xml` with a token, a kubeconfig. The next job, possibly from a different repository, reads them.
2. **Process and daemon state.** A Docker daemon shared between jobs means shared images, shared volumes, shared networks, and the ability for one job to inspect or attach to another's containers. Access to the Docker socket is root on the host.
3. **Environment and credential caches.** Cloud CLI credential caches, SSH agents, `kubectl` contexts, and anything the previous job exported to a profile script.
4. **Poisoned caches and tooling.** A malicious job modifies a tool on the `PATH`, a Gradle init script, a Maven `settings.xml`, or the local dependency cache - and every subsequent build on that runner is compromised silently.

The mitigation is **ephemeral runners**: one job per runner, then destroy it. Actions Runner Controller on Kubernetes gives you this natively; on VMs it is an autoscaling group with `--ephemeral` registration and instance termination after each job. Additionally: never allow the runner to be triggered by untrusted code (fork PRs go to hosted runners), do not give the runner ambient cloud credentials - use OIDC per job, and do not mount the Docker socket; use a rootless or nested builder.

### Q34. Ephemeral runners on Kubernetes

Actions Runner Controller runs a controller in the cluster that maintains a set of runner pods registered as ephemeral, self-hosted runners. It listens to GitHub's webhook or polls the queue, sees pending jobs for its runner labels, and scales the runner set up; each pod takes exactly one job, then exits and is replaced. Scale-down is by terminating idle pods after a configurable window.

The trade-off against a warm pool:

- **Ephemeral**: perfect isolation, no state leakage, no drift. Cost: cold start on every job - pod scheduling, image pull, then an empty Docker layer cache and an empty dependency cache. For a Java build that can be two to four minutes of pure overhead.
- **Warm pool** (`minRunners > 0`, or non-ephemeral runners): jobs start instantly and caches are warm. Cost: idle spend, and non-ephemeral runners reintroduce every problem in Q33.

The resolution I use is **ephemeral runners with a warm minimum and externalized caches** - keep a small floor of already-scheduled, image-pulled pods so the scheduling latency is hidden, and push the dependency and layer caches to a remote cache (a registry-backed BuildKit cache, an S3-backed Gradle cache) so a cold pod is still fast. That gets you isolation and most of the warmth.

### Q35. What to cache and the correct key

| Build | Cache | Key |
| --- | --- | --- |
| Maven | `~/.m2/repository` | Hash of all `pom.xml` files, plus the runner OS and JDK version |
| Gradle | `~/.gradle/caches` and `~/.gradle/wrapper` | Hash of `*.gradle*`, `gradle-wrapper.properties` and version catalogs, plus OS and JDK |
| Docker | BuildKit layer cache, exported to the registry or to a cache backend | Handled by BuildKit via layer digests; you provide `cache-from`/`cache-to` and let content addressing do the keying |

Two rules make caching correct rather than merely fast.

**The key must be a hash of everything that determines the cache's content.** If the key omits the JDK version, a JDK upgrade silently reuses artifacts compiled against the old one. If it omits the OS, native dependencies mismatch.

**Restore keys must be a prefix hierarchy, and the fallback must be safe.** `maven-${{ hashFiles('**/pom.xml') }}` with a restore fallback of `maven-` is fine for a dependency cache, because a stale dependency cache is a superset that Maven will top up. It is *not* fine for a build-output cache, where a partial restore produces stale classes. Cache dependencies loosely; cache build outputs strictly or not at all.

### Q36. How a cache poisons a build `[T]`

1. **The key is under-specified.** The cache key does not include something that affects the output - JDK version, OS, a code generator version, a build flag - so a build restores artifacts produced under different conditions. The classic is a Gradle build cache hit across a compiler upgrade.
2. **A mutable coordinate is cached.** A `-SNAPSHOT`, a version range, or a `latest` tag resolves once, gets cached, and every subsequent build uses the frozen resolution while the source of truth moves. The build is now reproducible and wrong.
3. **The cache is writable by an untrusted job.** A pull-request build writes to a cache scope that the mainline build reads. On GitHub Actions caches are scoped by branch with fallback to the default branch, so a fork PR generally cannot write to `main`'s scope - but on a self-hosted runner with a shared filesystem cache, or a shared remote cache without per-scope authorization, it can. That is a supply-chain attack, not a bug.
4. **Corruption or partial restore.** An interrupted upload, a partially-extracted archive, a cache written while a build was still running. The build then sees a half-populated directory and behaves unpredictably.

Defenses: hash everything relevant into the key; never cache mutable coordinates; segregate cache scopes by trust level and make untrusted builds read-only; and always have a "clear cache and rebuild" path that a developer can trigger without a platform team, because you will need it.

### Q37. Gradle build cache, dependency cache and daemon

- **Dependency cache** (`~/.gradle/caches/modules-2`) - avoids re-downloading artifacts. Saves network time.
- **Build cache** (`~/.gradle/caches/build-cache-1`, or a remote HTTP/S3 cache) - avoids re-*executing* tasks whose inputs are unchanged, restoring the outputs instead. This includes `compileJava` and `test`.
- **Daemon** - keeps a warm JVM with a loaded, JIT-compiled Gradle and a populated in-memory file-system and configuration cache.

On a *warm* CI runner, the **build cache** is the biggest win by a wide margin, and specifically the remote build cache. The dependency cache saves download time, which is seconds; the daemon saves JVM start-up and configuration time, which is also seconds and is only available if the runner persists. The build cache can skip the compile and test tasks entirely for unchanged modules, which on a multi-module Java build is minutes.

The caveat is that the build cache only pays if the tasks are **cacheable and their inputs are correctly declared**. A task with an undeclared input produces wrong cache hits; a task with an over-declared input (an absolute path, a timestamp, the full git directory) never hits. Getting real value from a remote build cache is a project, not a flag.

### Q38. Matrix builds

You parallelize across dimensions where the *same* work must be repeated under different conditions: JDK versions for a library that supports several, operating systems, database engines for an integration suite, or shards of a test suite.

A matrix costs more than it saves when:

- **Each cell has significant fixed overhead** relative to its work. Twenty cells at 90 seconds of setup and 20 seconds of tests is 30 minutes of billed runner time to save nothing in wall clock.
- **Cells contend on a shared resource** - one test database, one registry rate limit, one license server. You have bought parallelism you cannot use.
- **The cells are not independent** and you end up with `max-parallel: 1`, which is a for-loop with extra billing.
- **The dimensions are not real.** Testing on three JDKs for a service that only ever runs on one is pure cost; that matrix belongs on a library, not a service.

For test sharding specifically, the right shard count is where wall clock stops improving - usually well before the point where runner cost stops rising - and the sharding must be balanced by historical duration, not by file count.

### Q39. Flaky test detection and policy

**Detection**, automatically:

- **Re-run failures once and record the outcome.** A test that fails then passes with no change is flaky by definition. Record it; do not just let the re-run mask it.
- **Track per-test pass/fail history keyed by commit.** A test that has both passed and failed on the same commit SHA is definitively flaky.
- **Watch for suspicious signals**: tests that fail only in certain shard orders, only on certain runners, or only under parallel execution.

**Policy** when found:

1. **Quarantine immediately** - move it out of the merge gate so it stops blocking everyone, and file it with an owner and a deadline. A flaky test in the gate is worse than no test, because it teaches people to re-run without looking.
2. **Fix or delete within a bounded window.** Two weeks. A quarantined test that nobody fixes is a test nobody values.
3. **Track the flake rate as a platform metric** with a target, and report it. Individual flakes are a team problem; a rising flake rate is a platform problem.

The part people miss: a flaky test is frequently a **flaky system**. Time dependence, ordering dependence, shared state and race conditions in tests often mirror real concurrency bugs in the code. Deleting the test without looking discards a real signal.

### Q40. Zero flakes after quarantine `[T]`

It is a warning sign because the failure rate did not go to zero - the *visibility* of failures went to zero. Quarantine removes the alarm, not the fire. Two specific risks:

1. **Quarantine as a garbage bin.** Tests accumulate in it, coverage of real behavior silently drops, and eventually a genuine regression is caught by a quarantined test that nobody reads.
2. **The underlying race is real.** As above - a test that is flaky because of a timing assumption often reflects a timing assumption in the code, and you have just stopped looking at it.

What I put in place:

- **A quarantine budget and expiry.** A hard cap on the number of quarantined tests, and an automatic failure of the pipeline when a test has been quarantined beyond its deadline. Quarantine must be uncomfortable.
- **Quarantined tests still run**, on a nightly job, with results reported to the owning team. They just do not block the merge.
- **The flake rate is a visible metric**, so removing tests from the gate makes a number go up rather than down.
- **A root-cause requirement**: the ticket must state why it was flaky, not just that it was.

*Hook: a flaky test that turned out to be a genuine race condition.*

### Q41. Computing the affected set correctly

Correctly means: the affected set must be a **superset** of everything the change can influence, computed from a dependency graph that includes every input, not just source imports.

The inputs that must be in the graph:

- Compile-time dependencies between modules, transitively.
- **Test-only dependencies** - a test fixture module, shared test data.
- **Runtime and resource dependencies** - a shared configuration file, a schema, a protobuf or OpenAPI definition, a shared Dockerfile or base image.
- **The build system itself** - a change to a shared Gradle convention plugin, a root `pom.xml`, a CI workflow, or a tool version affects everything. This must map to "build everything".

The algorithm: hash each target's inputs, compute the set of targets whose input hash changed, then take the transitive *reverse* closure - everything that depends on a changed target, directly or indirectly.

Guardrails, because the graph will be wrong at some point: a scheduled full build on the mainline so drift surfaces within a day; a rule that any change outside a known module boundary triggers a full build (fail open, not closed); and periodic verification that the graph's declared dependencies match actual usage.

### Q42. Path filters missed the test `[T]`

Path filters answer "did files under this directory change" and nothing else. They have no model of *dependency*, so they are wrong in both directions:

- **False negative** (the dangerous one): service A's test would have caught the bug, but the change was in shared library B. The filter for A's pipeline only matches `services/a/**`, so A never built. This is exactly the described failure.
- **False positive**: a README change under `services/a/` triggers the full pipeline.

They also fail on changes with no path at all - a dependency version resolved from a range, a base image tag that moved, a change in a different repository.

What replaces them is a **content-addressed build graph** as in Q41: dependencies declared, inputs hashed, affected set computed as the reverse transitive closure. Bazel, Gradle with a well-declared project graph, Nx, Turborepo, or Pants all do this; the tool matters less than the fact that dependencies are *declared and verified* rather than inferred from directory layout.

If a full graph is out of reach, the pragmatic middle is: path filters plus an explicit hand-maintained "these paths trigger everything" list covering shared code, build config and CI definitions - and accept that it will be wrong occasionally, backed by a nightly full build.

### Q43. Quality gates and the urgent fix

Where each check belongs:

- **Pre-commit hook**: format, and the fastest secret scan. Advisory, because hooks can be skipped.
- **Pull request, blocking**: compile, unit tests, secret scan, dependency policy (license and known-malicious packages), and static analysis rules with near-zero false positives.
- **Pull request, advisory**: coverage delta, style suggestions, the noisier static analysis categories, informational CVEs.
- **Post-merge / nightly**: full SAST, DAST, the expensive scans, and the full build if you use change detection.
- **Admission / deploy time**: signature and provenance verification, manifest policy. These are not developer-facing gates; they are the last line.

When a gate blocks an urgent fix, the answer is **an explicit, logged override**, not a disabled gate. A break-glass label on the PR that requires a second approver, records who used it and why, and creates a follow-up item automatically. Two properties matter: it is *available* - otherwise people find an unmonitored route, like pushing an image by hand - and it is *visible*, so overuse is a fact rather than a rumour. A gate with no escape hatch gets removed after the first incident it blocks.

### Q44. Versioning a shared workflow across 30 repositories

The mechanism: shared workflows live in their own repository and are referenced as `uses: org/ci-workflows/.github/workflows/java-service.yml@<ref>`. The `ref` is the version.

The policy that makes this survivable:

1. **Consumers pin to a tag, never to a branch.** `@v2` (a moving major tag) for teams that want automatic patches; `@v2.3.1` or a commit SHA for teams that need determinism. Never `@main` - that is a live edit to 30 pipelines.
2. **Maintain moving major tags.** `v2` is re-pointed to each `v2.x.y` release. This is exactly how GitHub's own actions work, and it gives consumers a choice between stability and currency.
3. **Breaking changes go to a new major**, and both majors are supported for a defined window.
4. **Roll out by cohort.** Release `v3`, migrate two willing repositories, watch, then open automated PRs for the rest in batches. Never re-point a moving tag to a breaking change.
5. **Test the workflow itself.** The workflow repository has its own pipeline that exercises the reusable workflow against a representative sample repository on every change.
6. **Deprecation must be loud** - the old version emits a warning annotation on every run with a date, so nobody discovers the removal from a red build.

### Q45. Concurrency control

The mechanism is a named concurrency group scoped to what must be serialized:

```yaml
concurrency:
  group: deploy-${{ github.workflow }}-${{ inputs.environment }}
  cancel-in-progress: false
```

Two decisions matter. **The group name defines the mutual exclusion domain** - for a deploy it should be the service *and* environment, so deploying service A to staging does not queue behind service B. **`cancel-in-progress` is a correctness decision, not a cost one**: for CI on a pull request, cancel superseded runs, because only the latest commit matters. For a deploy, never cancel - a half-applied rollout that is killed mid-flight leaves the system in an undefined state.

The failure mode if you get it wrong: two deploys of the same service race, and the later one's rollout is overwritten by the earlier one's, so production ends up running the *older* image while both pipelines report success. With GitOps this is less acute because the desired state is a git commit and the reconciler converges - but you can still get an ABA sequence where the observed state flaps.

The stronger version, for anything critical, is a lock the deploy target itself owns - the GitOps repository's commit history, or a lease resource in the cluster - because CI-level concurrency does not protect against a human running the deploy by hand.

### Q46. Pipeline observability

What I instrument about the pipeline itself:

- **Duration**, p50 and p95, per workflow and per job. The p95 is the number developers actually experience on a bad day.
- **Queue time** separately from execution time. Rising queue time means a runner capacity problem, not a build problem, and the fixes are completely different.
- **Success rate**, split into genuine failures and infrastructure failures. Conflating these hides a degrading platform behind "the build is flaky".
- **Cache hit rate** per cache.
- **Cost** per workflow and per repository.
- **Flake rate** and quarantine count.
- **Time from merge to production**, which is the metric that actually matters and is usually owned by nobody.

The leading signal is **queue time p95** together with **infrastructure-failure rate**. Both degrade before developers complain, because developers attribute a slow or occasionally-failing build to bad luck long before they report it. Duration degrades slowly and gets normalized; queue time spikes are sharp and unambiguous.

I would emit these as metrics to the same system as production metrics, with an SLO, because a pipeline is a production system for the engineering organization.

### Q47. CI cost tripled `[A]`

**Attribute first.** The most common outcome of a cost investigation is discovering that 70 percent of spend is three workflows nobody looks at.

1. Break the bill down by repository, workflow, job and runner type, and by *billed minutes* rather than wall clock - a 20-way matrix at 2 minutes each bills 40 minutes.
2. Separate the two possible causes: **more runs** (higher commit volume, more triggers, retries, scheduled jobs) or **more cost per run** (longer builds, bigger runners, cache misses, more matrix cells). The remedies do not overlap.
3. Look at the ratio of pull-request builds to mainline builds, and at how many runs are superseded - a PR with 12 pushes that runs the full pipeline 12 times without cancellation is pure waste.

**What I change first**, in order of ratio of saving to effort:

1. **`cancel-in-progress` on PR workflows.** Usually a double-digit percentage saving, one line, zero risk.
2. **Fix cache hit rates.** A cache that never hits is paying full price for every build; this is often a mis-specified key, not a capacity problem.
3. **Trim the matrix and the scheduled jobs.** Nightly full builds on 40 repositories that nobody reads are a common find.
4. **Move heavy, long-running jobs to self-hosted or larger-but-fewer runners** where the per-minute economics are better; measure, because a bigger runner that halves the time is often cheaper.
5. **Move non-gate work off the pull-request path** to post-merge or nightly.

**What I would not do first**: cut test coverage or security scanning. Those trade a visible cost for an invisible one, which is the trade this exercise exists to avoid.

*Hook: a CI cost investigation and the single change that produced most of the saving.*

---

## 4. Build and dependency supply chain

### Q48. SBOM basics

A software bill of materials is a machine-readable inventory of the components in a piece of software - name, version, supplier, license, and a unique identifier such as a package URL or CPE - together with the relationships between them.

The two formats that matter are **SPDX** (ISO standard, license-provenance heritage, mandated in several government contexts) and **CycloneDX** (OWASP, security-first, richer vulnerability and dependency-relationship modelling). CycloneDX is generally the easier one to act on; SPDX is often the one an auditor asks for. Producing both is cheap.

**Where in the pipeline**: at build time, from the build, and attached to the artifact by digest. Not from the source repository afterwards, and not by scanning the running system - those answer different questions (see Q49). The SBOM should be generated in the same job that produces the image, signed, and pushed as an attestation alongside it, so that "the SBOM for what is running" is a digest lookup rather than a reconstruction.

### Q49. Source SBOM versus image SBOM

- **From source** (parse the dependency manifests and lock files): captures declared direct and transitive application dependencies with accurate version and license data, and it is available before anything is built. It **misses** everything the application does not declare - the base image's OS packages, the JDK itself, native libraries, anything installed by a `RUN apt-get`, and anything copied in from another stage. It also reports what was *declared* rather than what was *resolved and packaged*.
- **From the built image** (scan the layers): captures the complete, actually-shipped filesystem - OS packages, the JRE, embedded JARs, native libraries. It **misses** provenance and intent - which dependency is direct and which is transitive, which build target pulled it in, and often the precise license metadata that only the source manifest has. Fat JARs and shaded or relocated dependencies are frequently under-detected, because the original coordinates are gone.

The correct answer is that you generate both and merge them, keyed to the same artifact digest. In practice a lot of estates only generate the image SBOM and then cannot answer "which service depends on Log4j directly", which is the question that gets asked during an incident.

### Q50. Dependency confusion and typosquatting

**Typosquatting** is publishing a package with a name close to a popular one (`commons-lang` versus `common-lang`) and waiting for a typo or an autocomplete mistake.

**Dependency confusion** is subtler and more dangerous. If a build resolves a coordinate across multiple repositories - a private one for internal artifacts, a public one for open source - many resolvers pick the *highest version found anywhere*. An attacker who learns your internal group and artifact ID publishes version `99.0.0` of it to the public repository, your build resolves the public one, and their code executes in your build with your build credentials.

The configuration that prevents it:

1. **Scope isolation by namespace.** Reserve your organization's group ID or scope publicly so nobody else can publish under it.
2. **Explicit repository routing.** Configure the resolver so internal coordinates resolve *only* from the internal repository - Maven `mirrorOf` with exclusions, Gradle `exclusiveContent`, npm scoped registry configuration. This is the control that actually works, because it removes the ambiguity rather than trying to win a version comparison.
3. **A single proxying repository** (Nexus, Artifactory, CodeArtifact) with a group that orders the internal repository first and, critically, does not fall through to the public repository for internal groups.
4. **Pin versions and use lock files** so an unexpected higher version cannot be silently selected.

### Q51. Higher public version of an internal artifact ID `[T]`

What happens depends on how the proxy is configured, and this is precisely the question.

- If the proxy exposes a **virtual/group repository** that merges the internal hosted repository and the public proxy, the resolution depends on the group's ordering and on the resolver's version selection. Maven asks each repository in order for the metadata and, for a fixed version, takes the first repository that has it - so ordering saves you *if the version is pinned*. For a **version range or a `LATEST`/`SNAPSHOT` resolution**, Maven merges metadata across repositories and takes the highest, and the attacker's `99.0.0` wins.
- Gradle's default is to try repositories in declaration order for each module, but with dynamic versions or with multiple repositories declared it will resolve to the highest available version across them.

So the settings that decide it are: **whether the version is pinned or dynamic**, and **whether internal coordinates are routed exclusively to the internal repository**. Pinned versions plus exclusive routing means the attack does nothing. A dynamic version plus a merged group means the attacker's artifact executes in your build.

The additional control worth naming: the proxy should be configured to **not** proxy internal group IDs to the public repository at all - Artifactory exclude patterns, Nexus routing rules, CodeArtifact's upstream package origin controls - so a typo in a build file fails to resolve rather than resolving to something hostile.

### Q52. Lock files and reproducible resolution

**Maven** has no lock file. `pom.xml` version declarations plus `dependencyManagement` and a BOM give you determinism *if every version is pinned and nothing uses a range* - and Maven's nearest-wins resolution means the resolved graph can change when an unrelated dependency's own dependencies change. The Maven Enforcer plugin (`requireReleaseDeps`, `banDynamicVersions`) and `dependency:tree` are how you verify. `mvn dependency:lock`-style plugins exist but are not standard practice.

**Gradle** has a real lock file: `dependencyLocking` writes `gradle.lockfile` with the exact resolved versions per configuration, and subsequent resolutions fail if they would differ. Combined with the version catalog and `--write-locks` for deliberate updates, that is a genuine guarantee.

What neither guarantees: that the *artifact bytes* for a given coordinate are unchanged. Both ecosystems allow (Maven Central does not, but internal repositories often do) republishing under the same coordinate. Gradle's `dependencyVerification` with checksums and signatures closes that gap; Maven needs a plugin or a policy on the repository.

The practical answer for a Java estate: pin everything, ban dynamic versions with Enforcer, use a BOM for coherent version sets, and turn on dependency verification for anything security-critical.

### Q53. Nearest-wins versus highest-wins

- **Maven: nearest-wins.** When the same artifact appears at multiple depths in the tree, the one with the shortest path from the root wins; ties are broken by declaration order. This is what surprises people, because it means a *downgrade* can happen implicitly - a direct dependency on version 1.0 defeats a transitive requirement for 2.0, and the code that needed 2.0 fails at runtime with a `NoSuchMethodError`.
- **Gradle: highest-wins** by default, with rich conflict resolution (strict versions, rejections, capability conflicts). This surprises people differently: you get a version nobody declared, and a transitive upgrade can pull in a major version with breaking changes.

Maven's rule is the more dangerous one because its failure is a runtime `LinkageError` rather than a build-time conflict, and because `dependencyManagement` in a parent POM silently overrides everything below it regardless of depth.

**Diagnosing the resolved graph**: `mvn dependency:tree -Dverbose` shows omitted-for-conflict entries and the winner; `mvn dependency:analyze` catches used-but-undeclared and declared-but-unused. On Gradle, `./gradlew dependencies --configuration runtimeClasspath` and, better, `dependencyInsight --dependency <name>`, which explains *why* a version was selected. The habit worth having is to check the resolved graph in CI - a build that publishes its resolved dependency list makes Q29 a non-event.

### Q54. SCA, SAST, DAST and container scanning

| | Analyzes | Catches uniquely |
| --- | --- | --- |
| **SCA** | The dependency manifest / lock file / SBOM against a vulnerability database | Known CVEs in third-party code, and license violations. Cannot see your own code. |
| **SAST** | Your source or bytecode, statically | Vulnerable patterns you wrote - injection, unsafe deserialization, hardcoded secrets, path traversal. Cannot see runtime configuration or third-party internals. |
| **DAST** | The running application, from the outside | Configuration and deployment issues - missing headers, exposed endpoints, auth bypass, TLS problems - and anything that only exists when the system is assembled. Cannot see code paths it does not reach. |
| **Container scanning** | The image layers - OS packages, embedded binaries | Vulnerabilities in the base image and in anything installed outside the build tool's knowledge: OpenSSL, glibc, the JRE, curl. |

The overlaps matter less than the gaps: SCA misses your code, SAST misses the environment, DAST misses unreached paths, container scanning misses application logic. An estate with only SCA - which is common, because it is the cheapest to adopt - has no coverage of its own code at all.

Two additions worth naming at principal level: **IAST** (instrumented runtime analysis, far lower false positives than DAST) and **secret scanning**, which is not any of the four and catches more real incidents than the rest combined.

### Q55. 240 critical CVEs in the base image `[T]`

The number is almost certainly not actionable as stated, and the response is triage, not a Jira epic with 240 tickets.

1. **Check what is being scanned.** A `latest`-tagged full OS base image scanned against every package in the distribution produces hundreds of findings, most of them in packages the application never invokes. Confirm the scanner is looking at the shipped image, not a build stage.
2. **Update the base image first.** A single base image bump usually eliminates 80-90 percent of the findings for zero application risk. Do this before analyzing anything - it is faster than triage.
3. **Filter by reachability.** A CVE in a package with no executable path from the application is not exploitable. Reachability analysis tools, or simply the observation that the package is not installed in the final stage, dispose of most of the remainder.
4. **Filter by exploitability in context.** Is the vulnerable code path reachable from untrusted input? Is the service internet-facing? Is there a compensating control - no shell in the image, read-only root filesystem, network policy?
5. **Record the decisions as VEX** (Q56) so the next scan does not re-litigate them and so an auditor can see the reasoning.
6. **Then fix what remains**, on a severity-and-exploitability schedule with real deadlines.

The organizational point: a gate that fails on "any critical CVE" will be disabled within a month. A gate that fails on "any *reachable* critical CVE with a fix available, older than the SLA" is one people can live with. Choose the second, and make the base image update automated and continuous so this does not accumulate again.

*Hook: a CVE triage where the honest answer to most findings was "not exploitable here".*

### Q56. Reachability and VEX

"Vulnerable dependency present" means the artifact is on the classpath or in the image. Exploitability requires four additional things: the vulnerable *code path* exists in your configuration, it is *reachable* from your code, it is reachable from *untrusted input*, and no compensating control blocks it. Log4Shell was the case where all four held for almost everyone; most CVEs fail at least one.

Reachability analysis walks the call graph from your entry points into the dependency to determine whether the specific vulnerable method is invocable. It is not perfect - reflection, dynamic dispatch, service loaders and configuration-driven instantiation all defeat static analysis - so it should reduce the queue, not close it silently.

**VEX** (Vulnerability Exploitability eXchange) is the standard way to record the decision: for a given product, a given vulnerability, a status of `not_affected`, `affected`, `fixed` or `under_investigation`, with a justification (`vulnerable_code_not_present`, `vulnerable_code_not_in_execute_path`, `inline_mitigations_already_exist`, and so on). It is expressed in CycloneDX or OpenVEX and attached to the artifact as an attestation.

The reason this matters at principal level: without VEX, every scan re-surfaces every accepted finding, the queue never shrinks, and the team stops reading it. VEX turns triage from a repeated cost into a one-time one, and it is the artifact the auditor actually wants.

### Q57. Dependency update policy

| Change | Policy |
| --- | --- |
| Patch versions of well-known libraries, all tests pass | Auto-merge |
| Security patches, any severity, fix available | Auto-merge, and prioritized ahead of the batch |
| Minor versions | Auto-merge for internal and low-risk libraries; review for the framework and anything on the security path |
| Major versions | Always human review, one at a time, never batched |
| Spring Boot / framework BOM bumps | Human review, own PR, own canary |
| Build plugins and CI actions | Review, because they run with build credentials |

Batching rules: group patch updates weekly into one PR per ecosystem to avoid 40 PRs a week; never batch a major with anything; never batch across the framework boundary.

The controls that make auto-merge safe are not in the update policy at all - they are the test suite, the canary and the rollback. Auto-merging dependency updates into an estate with no progressive rollout is how Q29 happens. I would also require that auto-merged updates still go through the full deployment pipeline including canary analysis, and that the deployment event records that it was a dependency update, so incident triage can find it.

### Q58. Sigstore and keyless signing

**What is signed**: the artifact's digest - for an image, the `sha256` of its manifest. Signing is over the digest, not the tag, which is why tag mutability does not undermine it.

**Where the signature lives**: for container images, cosign pushes the signature to the registry as a separate OCI artifact whose tag is derived from the subject digest (`sha256-<digest>.sig`), or as an OCI 1.1 referrer. So the signature travels with the image and requires no separate infrastructure.

**Keyless signing**: instead of a long-lived private key that you must store, rotate and protect, cosign:

1. Obtains an OIDC identity token from the CI environment - for GitHub Actions, a token asserting the repository, workflow, ref and trigger.
2. Generates an ephemeral key pair, and asks **Fulcio** (the CA) for a short-lived certificate (about 10 minutes) binding the public key to that OIDC identity.
3. Signs the digest, then publishes the signature and certificate to **Rekor**, a public append-only transparency log, which timestamps the entry.
4. Discards the private key.

What it attests is therefore an **identity and a context**, not possession of a secret: "this digest was signed by the GitHub Actions workflow `.github/workflows/release.yml` in repository `org/service` on ref `refs/heads/main`". Verification checks the Rekor entry, checks the certificate chain to Fulcio, and - critically - checks that the certificate's identity claims match a policy you specify. Verifying a signature without pinning the expected identity is verification theater: anyone can sign anything keylessly.

### Q59. SLSA levels

SLSA (Supply-chain Levels for Software Artifacts) describes increasing guarantees about the *build process*, in the current v1.0 build track:

- **Build L1** - provenance exists. The build platform produces a document saying what was built, from what source, by what process. It is not necessarily trustworthy; it just exists and is available. This is a documentation-level guarantee.
- **Build L2** - provenance is **signed** by the build platform, and the build runs on a hosted platform rather than a developer's machine. You can now verify the provenance was not forged by the person who ran the build, though a compromised build platform could still forge it.
- **Build L3** - the build platform provides **strong tamper resistance**: builds are isolated from each other, the signing key is inaccessible to the build itself (so user-defined build steps cannot forge provenance), and the provenance is generated by the platform rather than by the build.

Realistically achievable on hosted CI: **L2 is straightforward** on GitHub Actions today - `actions/attest-build-provenance` produces signed provenance with a few lines. **L3 is achievable** using the official SLSA reusable workflows, which run the provenance generation in a separate, isolated job whose OIDC identity the build job cannot assume. The practical obstacle to L3 is not the tooling but the discipline: no self-hosted runner with shared state, no privileged steps, and a build that does not need secrets.

The honest framing for an interview: L1 and L2 are configuration; L3 is an architectural constraint on how you build.

### Q60. In-toto attestations and verification

An in-toto attestation is a signed JSON document in a standard envelope (DSSE) with three parts:

- **`subject`** - what the statement is about: a list of artifact names and their digests.
- **`predicateType`** - a URI naming the kind of statement (SLSA provenance, SBOM, test results, vulnerability scan).
- **`predicate`** - the statement itself. For SLSA provenance: the builder's identity, the build type, the source repository and commit, the build parameters and entry point, the resolved dependencies, and the build's start and finish metadata.

The signature is over the whole envelope, so the binding between "this digest" and "these claims" is what is cryptographically protected.

**Verification at deploy time**, in an admission controller (Kyverno, Sigstore policy-controller, Connaisseur) or in the CD step:

1. Resolve the image tag to a digest, and from here on work only with the digest.
2. Fetch the attestations attached to that digest from the registry.
3. Verify the signature: certificate chains to the expected Fulcio root, and the Rekor entry exists.
4. **Verify the identity**: the certificate's OIDC claims match the expected repository, workflow path and ref. This is the step people skip.
5. **Verify the predicate content** against policy: the source repository is one of ours, the ref is `refs/heads/main`, the builder is the expected reusable workflow, and the build was not triggered by a fork.
6. Admit or reject.

### Q61. The gap between the signed image and the running container `[T]`

Signature verification proves that a specific digest was produced by a specific build. Everything after admission is outside its scope:

1. **Mutation after admission.** A mutating webhook, an operator, or a sidecar injector modifies the pod spec after verification - adding a container, changing an image, injecting a volume. If the verifying webhook runs before the mutating one in the chain, you verified something that is not what runs.
2. **The other containers.** Init containers, sidecars, ephemeral debug containers. A policy that verifies only `spec.containers[0].image` admits an unsigned sidecar with the same network namespace and often the same service account token.
3. **Runtime mutation of the container's contents.** The image is immutable; the running container's filesystem is not, unless the root filesystem is read-only. A process that downloads and executes code at start-up - an agent, a plugin loader, a `curl | sh` in an entrypoint - runs code that was never in the signed image.
4. **What the image does at runtime.** The signature says who built it, not that it is safe. A signed image containing a backdoor is a correctly signed backdoor.
5. **The node and the runtime.** A compromised kubelet or container runtime can run something other than what was admitted; the digest check happens at pull time, and image pull policy matters here.

Closing it: verify all containers including init and sidecars, order the admission webhooks so verification runs last, enforce a read-only root filesystem and drop the ability to fetch and execute, use `imagePullPolicy: Always` with digest references, and add runtime detection (Q243) because that is the only control that sees what actually executes.

### Q62. Internal artifact repository

Beyond caching, it solves:

- **Availability and reproducibility.** Maven Central, Docker Hub and npm all have outages and rate limits, and packages do get yanked. A proxy means your build does not depend on their availability, and a build from two years ago still resolves.
- **A control point.** It is the single place where you can enforce policy: block known-malicious packages, enforce license rules, prevent dependency confusion by routing internal groups exclusively (Q50), and require scanning before an artifact is usable.
- **Publication of internal artifacts** with access control and immutability guarantees.
- **Visibility.** One place that can answer "who is using this library version", which is the question you need answered within the hour when a CVE lands.
- **Egress reduction**, which is a real cost item at scale.

The new single point of failure is real: if the repository is down, nothing builds and nothing deploys. Mitigations: run it highly available with the storage backed by object storage rather than a local disk; keep a documented and *tested* bypass configuration that points builds at the upstream directly for emergencies; monitor it as a tier-one production service with its own on-call; and back up the hosted repositories, because a proxy cache can be repopulated but your own published artifacts cannot.

### Q63. Supply chain posture for a regulated Java estate `[A]`

**First quarter** - the controls with the best ratio of risk reduction to effort, and the ones an auditor asks for first:

1. **Secret scanning everywhere** - pre-commit, push protection, and a historical scan of every repository. This catches more real incidents than everything else on the list.
2. **Pin and verify.** Base images by digest, dependencies pinned, dynamic versions banned by Enforcer, third-party GitHub Actions pinned to commit SHAs.
3. **A single proxying artifact repository** with exclusive routing for internal namespaces, closing dependency confusion.
4. **SBOM generation and image signing** on every build, attached to the digest. Cheap to add, and it is the foundation everything else builds on.
5. **Admission control that verifies signature and identity** in production, starting in audit mode and moving to enforce.
6. **SCA and container scanning with a triage process and VEX**, with an SLA rather than a blocking gate on day one.
7. **OIDC federation for cloud access from CI** and removal of every long-lived cloud key from the CI system.

**Deferred**, deliberately:

- **SLSA L3** with isolated provenance generation. Valuable, but it constrains how every team builds and should follow the basics.
- **Reachability analysis tooling.** Buy it after triage volume proves the need.
- **Full in-toto policy chains** across multiple attestation types.
- **Hermetic, network-isolated builds.** The highest-value remaining control and the most disruptive; it needs the artifact repository and pinning to be solid first.
- **DAST and IAST**, which are application-security investments rather than supply-chain ones.

The sequencing principle: everything in the first quarter is either invisible to developers or a one-time change. Everything deferred changes how people work daily, and that requires the first group to have already demonstrated value.

*Hook: a supply chain control you introduced and how you handled the team resistance to it.*

---

## 5. Containers and image engineering

### Q64. What a container is

A container is a **process** (or process tree) on the host kernel, running with a set of kernel-enforced restrictions on what it can see and how much it can use:

- **Namespaces** restrict what it can *see*: PID, mount, network, UTS, IPC, user, cgroup, time.
- **cgroups** restrict what it can *use*: CPU, memory, IO, PIDs.
- **Capabilities, seccomp and LSMs** (AppArmor, SELinux) restrict what it can *do*: which syscalls, which privileged operations.
- **A union filesystem** (overlayfs) gives it a root filesystem assembled from read-only image layers plus a writable layer.

**What it is not**: it is not a virtual machine. There is no guest kernel, no hypervisor, and no hardware-level boundary. Every container on a node shares the host kernel, so a kernel vulnerability is a shared-fate vulnerability, and root in a container without a user namespace is root on the host if it escapes. It is also not a security boundary in the way a VM is - which is why gVisor, Kata and Firecracker exist for multi-tenant workloads.

Saying this clearly is worth a lot, because it grounds every later answer about pod security, `hostPID` and runtime detection.

### Q65. Namespaces and cgroup v2

| Namespace | Isolates |
| --- | --- |
| PID | Process IDs; the container's first process is PID 1 |
| Mount | The filesystem tree |
| Network | Interfaces, routes, iptables rules, ports |
| UTS | Hostname and domain name |
| IPC | System V IPC, POSIX message queues |
| User | UID/GID mapping - the one that lets root-in-container be an unprivileged UID on the host |
| Cgroup | The cgroup root the process sees |
| Time | Boot and monotonic clock offsets |

**cgroup v2 versus v1**, for memory and CPU:

- **Unified hierarchy.** v1 had a separate hierarchy per controller, which made consistent policy across CPU and memory awkward and led to inconsistent accounting. v2 has one tree with controllers enabled per subtree.
- **Memory**: v2 introduces `memory.low` (best-effort protection), `memory.high` (throttling rather than killing - the process is stalled and reclaim is forced) and `memory.max` (the hard limit, OOM kill). v1 only had a hard limit, so the only outcome was an OOM kill. v2's `memory.high` allows graceful degradation. Accounting for page cache and kernel memory is also unified rather than a separate `kmem` controller.
- **CPU**: `cpu.max` expresses quota and period together; **pressure stall information** (`cpu.pressure`, `memory.pressure`, `io.pressure`) is a v2 feature and is the best signal available for "this container is being throttled or starved", far better than utilization.

For the JVM the practically important change is that container detection and PSI-based throttling signals are cleaner on v2, and that Kubernetes' `MemoryQoS` feature uses `memory.high` to make eviction less abrupt.

### Q66. OCI image format and digests

An OCI image is a content-addressed graph:

- **Manifest** - a JSON document listing the config descriptor and the layer descriptors, each by media type, size and `sha256` digest. The image's digest is the `sha256` of this manifest.
- **Config** - a JSON blob with the runtime configuration (entrypoint, env, user, working directory, exposed ports) and the ordered list of layer diff IDs plus the build history.
- **Layers** - tar archives (usually gzip or zstd compressed), each a filesystem diff applied in order.
- **Index** (manifest list) - for multi-architecture images, a list of manifests by platform. Its digest is what a multi-arch tag points to.

**A tag is a mutable pointer** stored in the registry: a name-to-digest mapping that anyone with push access can change. `myimage:1.2.3` today and tomorrow can be different content with no record in your manifests.

**The digest is the content.** `myimage@sha256:abc...` cannot refer to different bytes, because the digest is computed over those bytes. The registry cannot lie about it, a man-in-the-middle cannot substitute it, and the client verifies it on pull. That is why every automated reference - deployment manifests, signatures, SBOM attachments, provenance subjects - is by digest, and why tags are for humans.

### Q67. Layer caching and the Java layout

The rules: each instruction produces a layer; a layer is cached if the instruction and all its inputs are unchanged; and **a cache miss invalidates every subsequent layer**. So instructions must be ordered from least to most frequently changing, and each `COPY` must bring in the smallest set of files that instruction actually needs.

```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

# Changes only when the build files change - so dependency download is cached
COPY pom.xml .
COPY src/main/resources/application.yml ./probe-only-if-needed
RUN mvn -B dependency:go-offline

# Changes on every commit
COPY src ./src
RUN mvn -B -o package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /build/target/app.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
```

The key move is splitting the `COPY` of `pom.xml` from the `COPY` of `src`, so the dependency resolution layer - the expensive one - survives a source change. For a multi-module build, copy every module's `pom.xml` first, which is fiddly enough that most teams script it.

Two refinements: use a **BuildKit cache mount** (`RUN --mount=type=cache,target=/root/.m2 mvn package`) so the dependency cache persists across builds *without* being a layer at all, which handles the `pom.xml`-changed case too; and see Q70 for splitting the application JAR itself into layers.

### Q68. One line in pom.xml invalidates everything `[T]`

**Mechanism.** `COPY pom.xml .` produces a layer whose cache key includes the file's content hash. Changing one line changes the hash, so that layer misses, and every instruction after it - including `RUN mvn dependency:go-offline`, which downloads several hundred megabytes - is re-executed. The layer cache is strictly ordered; there is no partial reuse.

There is often a second, worse mechanism: if the runner has no persistent layer cache at all (a fresh hosted runner), *every* build is a full miss and the eight minutes is unrelated to the `pom.xml` change.

**Fixes**, in order of effectiveness:

1. **BuildKit cache mounts.** `RUN --mount=type=cache,target=/root/.m2,sharing=locked mvn -B package`. The Maven repository lives in a cache mount that is not part of the image and is not invalidated by a layer miss, so changing `pom.xml` re-runs the download step but it only fetches the *new* dependency. This is the fix.
2. **Persist the BuildKit cache across CI runs** - `--cache-from`/`--cache-to` with a registry or S3 backend, or a persistent builder on a self-hosted runner. Without this, cache mounts do not survive between jobs on hosted runners.
3. **Build outside the Dockerfile.** Run Maven as a normal CI step with the standard `~/.m2` cache, then `COPY` the resulting JAR into a minimal image. This gives up build hermeticity but is simple and fast, and is what most Java pipelines actually do.
4. **Order more carefully** for multi-module builds so that a leaf module's POM change does not invalidate the parent's dependency resolution.

*Hook: a build you took from eight minutes to under two, and which change mattered.*

### Q69. Multi-stage builds

**Build stage**: the JDK, the build tool, the source, the test dependencies, any code generators, and the credentials needed to fetch dependencies. This stage can be large and messy; nothing in it ships.

**Runtime stage**: a minimal base, the JRE (or a `jlink`-produced runtime), the application artifact, and nothing else. No shell if you can manage it, no package manager, no build tool, no source.

Keeping build tooling out is mechanical - you start a new `FROM` and copy only named paths across:

```dockerfile
FROM eclipse-temurin:21-jdk AS build
# ... build ...

FROM eclipse-temurin:21-jre AS runtime
COPY --from=build /build/target/app.jar /app/app.jar
```

Three things to say beyond the mechanics:

- **Secrets must not be in a build stage layer either.** `COPY settings.xml` in the build stage leaves the token in that layer's tar, and while the layer does not ship, it does get pushed if you export build cache to a registry. Use `RUN --mount=type=secret` instead.
- **Name your stages and target them.** `--target build` lets CI run tests in the build stage without producing the runtime image, and lets you produce a debug variant with a shell from the same Dockerfile.
- **The final stage should be the last one** in the file, because `docker build` without `--target` builds the last stage - and stages that nothing depends on are skipped entirely by BuildKit, which is free parallelism.

### Q70. Spring Boot layered JARs

An executable Spring Boot fat JAR is one file, so it is one layer, so a one-line code change re-pushes the entire artifact - typically 40-80 MB.

`layertools` splits the JAR by change frequency into four layers, in this order:

1. **`dependencies`** - released third-party dependencies. Changes on a dependency bump; large.
2. **`spring-boot-loader`** - the loader classes. Almost never changes; tiny.
3. **`snapshot-dependencies`** - snapshot dependencies. Changes often if you use them; ideally empty.
4. **`application`** - your classes and resources. Changes on every commit; typically a few hundred kilobytes to a few megabytes.

```dockerfile
FROM eclipse-temurin:21-jre AS builder
WORKDIR /app
COPY target/app.jar app.jar
RUN java -Djarmode=layertools -jar app.jar extract

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/dependencies/ ./
COPY --from=builder /app/spring-boot-loader/ ./
COPY --from=builder /app/snapshot-dependencies/ ./
COPY --from=builder /app/application/ ./
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

**Effect on push size for a typical code change**: from the full JAR (say 60 MB compressed) down to the application layer alone (often 1-3 MB). Pull time on the node improves by the same ratio for any node that already has the dependency layers, which is most of them during a rolling update. The dependency layer only changes when dependencies change, which is weekly rather than hourly.

Buildpacks (`mvn spring-boot:build-image`) do this automatically and add more granular layering; the trade-off is less control over the base image.

### Q71. Base image selection

| Base | Size | Attack surface | Debuggability | Notes |
| --- | --- | --- | --- | --- |
| Full JDK | ~450 MB | Largest - compilers, shell, package manager | Best | Only for build stages |
| JRE (Debian-based) | ~230 MB | Shell, package manager, full libc | Good | Sensible default |
| Alpine JRE | ~150 MB | Shell (busybox), apk | Good | **musl libc** - see below |
| Distroless (`gcr.io/distroless/java21`) | ~180 MB | No shell, no package manager, no busybox | Poor - needs ephemeral debug containers | Best default for production |
| Scratch | Only what you add | Minimal | None | Requires a `jlink` static runtime; rarely worth it for the JVM |

**The glibc/musl issue.** Alpine uses musl libc, not glibc. Official OpenJDK builds for Alpine exist (`eclipse-temurin:21-jre-alpine`), so the JVM runs - but:

- **Native libraries in your dependencies** (Netty's native transports, snappy, tcnative, some JDBC drivers, Tesseract wrappers) ship glibc binaries and will fail to load or crash. This is the most common real breakage.
- **musl's default thread stack size is much smaller** (128 KB versus 8 MB), which surfaces as `StackOverflowError` in deeply recursive code.
- **musl's allocator behaves differently** under multi-threaded load - historically much worse fragmentation and contention for JVM-shaped workloads, which is why glibc-based images often show better throughput.
- DNS resolution differs (no NSS, different `search` behaviour), which bites in Kubernetes.

My default is **distroless for production and a Debian-based JRE where the team needs to `exec` in**, with Alpine only for genuinely size-critical cases where the dependency set has been verified to be pure Java.

### Q72. Works on Debian, SIGSEGV on Alpine `[T]`

The most likely cause is a **native library compiled against glibc being loaded on musl**. A JAR that bundles `.so` files - Netty's `netty-transport-native-epoll`, `netty-tcnative`, snappy, LZ4, a native JDBC or crypto provider - selects a Linux x86-64 binary, loads it, and the dynamic linking against glibc symbols that musl does not provide (or provides with different semantics) produces a segfault rather than a clean `UnsatisfiedLinkError`. The fix is to select the musl-specific classifier where the library publishes one (`linux-x86_64-alpine` for tcnative), or to move off Alpine.

Other things that change on musl, worth naming because they produce subtler failures:

- **Thread stack size** defaults to 128 KB versus glibc's 8 MB, so deep recursion or a framework with deep stacks throws `StackOverflowError` that never occurred on Debian. `-Xss` fixes it, and `-XX:ThreadStackSize` for VM threads.
- **Allocator behaviour.** musl's malloc has far less per-thread arena caching, so heavily multithreaded native allocation (Netty direct buffers, compression) shows higher contention and different RSS growth. This presents as "slower and uses more memory" rather than a crash.
- **DNS.** musl's resolver does not support NSS, queries all nameservers in parallel, historically had issues with search domains and with TCP fallback for large responses. In Kubernetes, this shows up as intermittent resolution failures.
- **Locale and charset.** musl ships minimal locale support, so anything relying on non-UTF-8 locales behaves differently.
- **`getaddrinfo` and IPv6 preference** differ, which changes connection behaviour in dual-stack clusters.

### Q73. JVM heap sizing in a container

Since JDK 10 (and backported to 8u191), the JVM is **container-aware**: `UseContainerSupport` is on by default, and it reads the cgroup limits rather than the host's `/proc/meminfo`. Specifically it reads `memory.max` (cgroup v2) or `memory.limit_in_bytes` (v1) for memory, and `cpu.max` or `cpu.quota`/`cpu.period` for CPU.

With no flags, the JVM sets the maximum heap to **25 percent** of the container memory limit (`MaxRAMPercentage` default). That is conservative to the point of wasteful for a container running one process, which is why you always set it explicitly.

**If you set `-Xmx` equal to the container memory limit, the pod gets OOMKilled.** The heap is not the JVM's memory footprint. The process also needs:

- **Metaspace** - class metadata; 50-250 MB for a Spring Boot application, and unbounded by default.
- **Code cache** - JIT-compiled code, up to 240 MB by default.
- **Thread stacks** - 1 MB each by default; 200 threads is 200 MB of reserved address space, with committed memory lower but non-trivial.
- **GC structures** - card tables, remembered sets; roughly 3-5 percent of heap for G1.
- **Direct byte buffers and memory-mapped files** - Netty, NIO, some drivers. `MaxDirectMemorySize` defaults to the heap size if unset, so this can silently double your footprint.
- **Native allocations** by the JVM itself and by any native libraries.
- **The rest of the container** - the JVM is not alone if you have an agent or a shell.

So `-Xmx` equal to the limit means the first significant non-heap allocation pushes the cgroup over `memory.max`, and the kernel OOM killer terminates the process. The JVM never gets a chance to throw `OutOfMemoryError`, so you get exit code 137 and no heap dump.

### Q74. MaxRAMPercentage and the non-heap budget

My default is **`-XX:MaxRAMPercentage=70`** for a typical Spring Boot service, with `-XX:InitialRAMPercentage` set to the same value when I want to avoid heap resizing pauses and I am confident about the footprint. I use percentages rather than `-Xmx` so that changing the pod's memory limit does not require a corresponding image or config change - one number, one place.

`InitialRAMPercentage` sets the starting heap; setting it equal to the max avoids the JVM growing the heap under load (which causes GC pauses and makes early memory behaviour misleading) at the cost of committing the memory immediately, which makes the pod's real footprint honest from the start. For a container with a fixed limit that is usually what you want.

**Accounting for non-heap**, concretely, on a 2 GiB limit:

| Item | Budget |
| --- | --- |
| Heap (`MaxRAMPercentage=70`) | 1434 MB |
| Metaspace (`MaxMetaspaceSize=256m`) | 256 MB |
| Code cache (`ReservedCodeCacheSize=128m`) | 128 MB |
| Thread stacks (200 × 1 MB, partially committed) | ~100 MB |
| Direct memory (`MaxDirectMemorySize=64m`) | 64 MB |
| GC and JVM native overhead | ~80 MB |
| **Total** | ~2062 MB - already over |

That table is the point: 70 percent is often too high for a service with a lot of classes and threads, and the way to find the real number is **Native Memory Tracking** (`-XX:NativeMemoryTracking=summary`, then `jcmd VM.native_memory`) plus watching container RSS, not arithmetic. I bound metaspace, code cache and direct memory explicitly - not to save memory, but so that a leak in any of them produces a clean `OutOfMemoryError` with a stack trace instead of a silent kill.

### Q75. OOMKilled with 40 percent heap `[T]`

The heap graph is measuring one region of a process whose limit applies to all of it. Where the memory actually went, in rough order of likelihood:

1. **Metaspace growth.** Unbounded by default. Dynamic proxy generation, a class loader leak from repeated redeployment, heavy use of code generation, or a library that generates classes per request. Grows quietly and never appears on a heap chart.
2. **Direct byte buffers / off-heap.** Netty, NIO, an HTTP client, a compression or serialization library. `MaxDirectMemorySize` defaults to `Xmx`, so a service with a 1.4 GB heap can allocate another 1.4 GB of direct memory before the JVM objects.
3. **Thread stacks.** A thread leak - an unbounded executor, a client library creating a thread per connection - costs 1 MB of stack each plus native structures. 500 leaked threads is 500 MB and no heap growth.
4. **Native memory from a library.** A native compression codec, a crypto provider, a JNI-based driver, or an APM agent's native buffers.
5. **Code cache.** Rare but real for long-running services with a lot of hot code, and it is capped at 240 MB by default.
6. **The page cache and the writable layer.** Files written inside the container count towards the cgroup's memory in v1 accounting, and logs written to the container filesystem are a classic. Reclaimable, but under pressure the kernel may kill first.
7. **Something else in the pod.** A sidecar, an agent, or an init container that did not exit. The memory limit is per container, but the pod-level and node-level pressure are not.

**How I would actually find it**: enable Native Memory Tracking and compare `jcmd VM.native_memory summary.diff` over time - it attributes JVM-internal native memory by category and immediately distinguishes metaspace, thread, code and GC growth. If NMT accounts for less than the RSS, the leak is outside the JVM, and the tool is `pmap`/`smaps` or jemalloc profiling. Also check thread count and loaded class count as metrics; both are cheap and both would have caught this before the kill.

*Hook: an OOMKill you diagnosed where the heap was innocent.*

### Q76. CPU limits, CFS throttling and the JVM

A Kubernetes CPU limit becomes a **CFS bandwidth control**: the cgroup gets `cpu.max = quota period`, typically a 100 ms period with a quota proportional to the limit. A limit of `500m` means 50 ms of CPU time per 100 ms period, summed across all threads. When the quota is exhausted, **every thread in the cgroup is descheduled until the next period begins** - up to 100 ms of complete stall.

Why this hurts the JVM specifically:

- **Parallel GC threads burn quota in a burst.** A G1 young collection that would take 5 ms of wall clock using 8 threads consumes 40 ms of quota. On a `500m` limit that is 80 percent of the period, so the collection itself is throttled and the pause stretches from 5 ms to tens or hundreds of milliseconds. The GC log shows a long "real" time with small "user" and "sys" times - the signature of throttling.
- **JIT compiler threads** compete for the same quota during warm-up, which is exactly when the application is slowest anyway.
- **Thread pools sized by `availableProcessors`** are sized for parallelism the quota does not permit, so you get more context switching for the same throughput.

**`availableProcessors`** on a container-aware JVM reports, in order of preference: `-XX:ActiveProcessorCount` if set; otherwise a value derived from the cgroup - the CPU **quota** divided by the period (rounded up) if a quota is set, else the CPU **shares** heuristic, else the cpuset size, else the host CPU count. So with `limits.cpu: 500m` it reports 1; with `limits.cpu: 2` it reports 2; **with only `requests.cpu` and no limit, there is no quota**, so the JVM falls back to shares or the host count and can report 64 on a large node - which is how a pod with a `200m` request ends up with 64 GC threads. That case is worth fixing with `-XX:ActiveProcessorCount` explicitly.

### Q77. Image size reduction, ranked

Ranked by actual impact for a Java service:

1. **Choose a smaller base.** Full JDK to JRE saves ~200 MB; JRE to distroless saves another 50 MB and most of the attack surface. This is one line and the biggest single win.
2. **Multi-stage build.** Removing the build tooling, source and test dependencies is the difference between shipping the toolchain and shipping the application.
3. **`jlink` a custom runtime.** A Spring Boot service typically needs a fraction of the JDK modules; a `jlink` runtime can be 50-70 MB instead of 180 MB. Costs build complexity and breaks on reflective module use.
4. **Layer the JAR** (Q70). This does not reduce total size but reduces *transferred* size per deploy by an order of magnitude, which is what actually affects rollout speed.
5. **Remove unnecessary dependencies.** Often finds an unused driver, a duplicated logging framework, or a test library on the runtime classpath.
6. **Compression choice** - zstd layers over gzip, if your registry and runtime support it.

**Where the weight actually is**: for a typical Spring Boot service on a JRE base, roughly 180 MB of base image and JRE, 40-70 MB of dependencies, and 1-3 MB of application code. So the base image and the dependency set are everything, and micro-optimizing the application layer is wasted effort. The two dependency-side offenders I usually find are a bundled Netty with all native transports, and an unshaded cloud SDK that pulls in every service client.

Worth saying: image size matters mostly for **pull latency on a cold node** during scale-out and incident recovery. If your nodes are warm and your layers are shared, a 400 MB image is not a problem worth a week of work.

### Q78. AppCDS

Class Data Sharing dumps the internal representation of loaded classes into an archive that the JVM memory-maps at start-up, skipping the parse-and-verify step for every class in it. **Default CDS** covers JDK classes and ships with the JDK. **AppCDS** extends it to application and library classes, which is where the win is for Spring - a Boot application loads 10,000-20,000 classes at start-up.

Creating it: run the application with `-XX:ArchiveClassesAtExit=app.jsa` (or the older two-step `-Xshare:dump` with a class list), bake the archive into the image, and run with `-XX:SharedArchiveFile=app.jsa`. Spring Boot 3.3+ makes this a first-class flow with `-Dspring.aot.enabled` and the CDS-friendly `java -Djarmode=tools -jar app.jar extract` layout, because the archive requires a stable, exploded classpath.

**Expected improvement**: typically **20-40 percent off JVM start-up** for a Spring Boot service - a 4-second start-up going to 2.5-3 seconds. Not the order of magnitude that native images give, but it costs almost nothing and changes no runtime semantics.

**What invalidates the archive**: any change to the classpath *string* (order, paths, added or removed JARs), a different JVM version or build, different relevant JVM flags (GC selection, compressed oops settings), and a different base directory layout. The JVM detects the mismatch and silently falls back to normal loading - which is the trap: your archive stops working and nothing fails, you just quietly lose the benefit. Verify it with `-Xshare:on` (which *fails* rather than falling back) in a test, and add a start-up-time assertion to CI.

### Q79. GraalVM native image

**Gain**: start-up in tens of milliseconds instead of seconds, memory footprint often a third to a half of the JVM's, no warm-up (peak performance immediately), and a much smaller attack surface with no bytecode to inject.

**Lose**:

- **Peak throughput**, typically 10-30 percent below a warmed-up C2-compiled JVM for long-running work, because the ahead-of-time compiler cannot use profile-guided optimization from the actual workload (PGO helps, and is a paid feature in Oracle GraalVM).
- **The JVM's observability ecosystem** - JFR support is partial, JMX is limited, heap dumps and most agent-based APM tooling do not work the way you expect. This is the one that hurts operationally.
- **Dynamic capability**: no runtime class loading, no dynamic proxies without configuration, no arbitrary reflection.
- **Build time and cost**: a native image build takes 3-10 minutes and needs several gigabytes of memory, so your CI gets slower and more expensive.

**What breaks at build time**: the closed-world assumption means everything reachable must be known statically. Reflection, dynamic proxies, JNI, resource loading by name, and service loaders all require reachability metadata. Spring's AOT processing generates most of this for Spring itself, but a third-party library without native metadata fails - sometimes at build time with a clear error, and sometimes at *runtime* with a `ClassNotFoundException` on a code path the build never explored, which is the worse case. Class initialization also moves: some classes are initialized at build time, which bakes their static state into the image, and a class that captures a timestamp, a random seed or an environment value at initialization produces a subtly wrong binary.

### Q80. Native images across the estate to cut cold start `[A]`

**Establish the actual problem first.** "Cold-start cost" means different things: scale-out latency during traffic spikes, rollout duration, cost of over-provisioning to hide start-up, or genuine scale-to-zero economics. Each has a different cheapest fix, and native image is the most expensive one on the list.

**Cheaper alternatives to evaluate first:**

- **AppCDS** (Q78) - 20-40 percent off start-up, near-zero cost, no semantic change.
- **Spring AOT without native** - `spring.aot.enabled` gives a meaningful start-up improvement on the JVM alone.
- **Fix the start-up work.** Most slow Spring services are slow because of eager connection pool initialization, classpath scanning, a slow discovery client, or a health check that waits on a dependency. This is often the single biggest win and it is free.
- **Provision differently.** Keep warm capacity, pre-pull images, use a HPA with a shorter stabilization window and better headroom. If the problem is scale-out latency, capacity is a direct answer.

**Where native genuinely wins**: workloads that scale to zero or scale very spikily (event handlers, batch triggers, functions), high-density deployments where the memory saving multiplies across hundreds of replicas, and CLI tools.

**Where it does not**: long-running, throughput-oriented services - which is most of an estate. There you pay 10-30 percent peak throughput, lose your profiling and APM tooling, and add build complexity, in exchange for a start-up improvement that only matters a few times a day.

**Recommendation**: no to a blanket migration. Yes to a pilot on one or two genuinely spiky services, with the throughput and observability regression measured rather than assumed. Adopt AppCDS estate-wide, because it is nearly free. Revisit native for new services with scale-to-zero characteristics.

**What would change my mind**: if the estate were moving to a serverless or scale-to-zero platform where idle capacity is the dominant cost; if the observability gap closed (JFR support in native images has been improving); or if a measured pilot showed the throughput regression to be under 5 percent for our workload shape.

*Hook: a start-up time investigation where the fix turned out to be eager initialization rather than the runtime.*

---

## 6. Kubernetes core - scheduler, controllers, probes and resources

### Q81. Control plane components

- **kube-apiserver** - the only component that talks to etcd, and the front door for everything else. Authentication, authorization, admission, validation, and serving watches.
- **etcd** - the datastore. Every object's desired and observed state lives here.
- **kube-scheduler** - watches for pods with no `nodeName` and binds each to a node by filtering (predicates) then scoring.
- **kube-controller-manager** - the built-in controllers: Deployment, ReplicaSet, Node, Job, EndpointSlice, and about thirty others, each running a reconciliation loop.
- **cloud-controller-manager** - the cloud-specific loops: node lifecycle, load balancer provisioning, route management.
- **kubelet** (on every node) - watches for pods bound to its node, calls the container runtime via CRI, runs probes, reports status.
- **kube-proxy** or an eBPF dataplane (on every node) - programs the node's Service routing.

**If the API server goes down, running workloads keep running.** The kubelet continues to run the containers it already knows about, restarts them on failure, and the dataplane keeps forwarding traffic because the iptables/IPVS/eBPF rules are already programmed on each node. What you lose is *change*: no new pods scheduled, no rescheduling on node failure, no Service endpoint updates, no scaling, no deployments, no `kubectl`. Existing traffic to healthy pods is unaffected; traffic to a pod that dies during the outage keeps being sent there, because nothing can update the endpoints.

That distinction - the dataplane is decoupled from the control plane - is the whole reason Kubernetes survives control plane outages, and it is what the question is testing.

### Q82. The reconciliation loop

The controller pattern: a controller watches one or more resource types, and on every event (and on a periodic full resync) it computes the difference between the **desired state** in the spec and the **observed state** in the status and the world, then takes the actions that reduce that difference. It writes what it did into `status`. It does not remember what it did last time.

**Level-triggered rather than edge-triggered** means the controller acts on the *current state*, not on the *event that told it something changed*. The event is only a hint that it is worth looking again.

Why that matters, concretely:

- **Missed events are survivable.** If a watch connection drops and the controller misses ten updates, the next resync sees the current state and converges anyway. An edge-triggered system would be permanently wrong.
- **Duplicate events are harmless**, because the action is idempotent - it is computed from the state, not from the event.
- **Order does not matter.** The controller does not need events in sequence, only the latest state.
- **It converges after any disruption** - a controller restart, an API server outage, a manual change - without a recovery procedure.

The cost is that reconciliation is *eventually* consistent and can be slow, and that a controller cannot easily express "do this exactly once", which is why one-shot operations in Kubernetes (Jobs, hooks) are awkward and why operators need careful idempotency.

### Q83. kubectl apply to a running container

1. **`kubectl`** resolves the resource, computes a patch (server-side apply sends the full intent with a field manager), and sends an HTTPS request to the API server.
2. **API server**: authenticates (certificate, token, OIDC), authorizes (RBAC), then runs **admission** - mutating webhooks first (sidecar injection, defaulting), then schema validation, then validating webhooks (policy engines), then quota.
3. The Deployment object is **persisted to etcd**. The API server returns 201. From `kubectl`'s point of view it is done, and nothing is running yet.
4. **Deployment controller** sees the new Deployment via its watch, creates a **ReplicaSet** with the pod template and a hash suffix.
5. **ReplicaSet controller** sees a ReplicaSet with 0 of N pods, creates N **Pod** objects with no `nodeName`.
6. **Scheduler** watches for unbound pods. For each: **filter** nodes (resource fit, node selectors, affinity, taints, volume topology, port conflicts), **score** the survivors (spread, least/most allocated, image locality, affinity weights), pick the best, and write a **Binding** which sets `nodeName`.
7. **kubelet** on that node sees a pod bound to it. It: creates the pod's cgroup sandbox; calls the **CNI** plugin to set up the network namespace, assign an IP and program routes; mounts volumes (calling **CSI** for persistent ones); pulls images via **CRI** (checking `imagePullPolicy` and pull secrets); runs **init containers** to completion in order; starts the application containers.
8. **Probes** begin. Once the readiness probe passes, kubelet updates the pod's status conditions.
9. **EndpointSlice controller** sees a ready pod matching a Service selector and adds it to an EndpointSlice.
10. **kube-proxy / CNI dataplane** on every node sees the EndpointSlice change and programs the node's forwarding rules. Traffic now reaches the pod.

Steps 8-10 are where the graceful-shutdown race lives (Q90), and step 2 is where every security control lives.

### Q84. Deployment, ReplicaSet and Pod

- **Deployment** owns the **rollout strategy**: it decides how many ReplicaSets exist, and how to shift replicas between them. It owns revision history and rollback.
- **ReplicaSet** owns exactly one thing: **maintaining a replica count** for one immutable pod template. It creates and deletes pods to match.
- **Pod** owns nothing; it is the scheduled unit.

A **rolling update** does not modify pods in place. The Deployment controller:

1. Computes the pod-template hash of the new template. If it matches an existing ReplicaSet, that one is reused (which is why a rollback is fast and why `rollout undo` scales the old ReplicaSet back up rather than creating one).
2. Creates a **new ReplicaSet** at 0 replicas.
3. Alternately **scales the new one up** and the **old one down**, bounded by `maxSurge` and `maxUnavailable`, waiting between steps for new pods to become *Ready* and for `minReadySeconds` to elapse.
4. When the new ReplicaSet is at full replicas and the old is at zero, the rollout is complete. The old ReplicaSet is kept (up to `revisionHistoryLimit`) as the rollback target.

So a rolling update **creates new pods and deletes old ones** - no pod is ever updated. That is why every rolling update is also a restart, and why anything cached in a pod's memory or local disk is lost on every deploy.

### Q85. maxSurge and maxUnavailable

For a Deployment with `replicas: 10`:

| Setting | Max pods running | Min available | Behaviour |
| --- | --- | --- | --- |
| `maxSurge: 25%`, `maxUnavailable: 25%` (default) | 13 (10 + 2.5 rounded up) | 8 (10 - 2.5 rounded down) | Fast; capacity can dip to 80 percent |
| `maxSurge: 25%`, `maxUnavailable: 0` | 13 | 10 | **Never loses capacity**; needs headroom for 3 extra pods |
| `maxSurge: 0`, `maxUnavailable: 25%` | 10 | 8 | No extra capacity needed; capacity dips |
| `maxSurge: 1`, `maxUnavailable: 0` | 11 | 10 | Safest and slowest - one at a time |

Rounding matters and is asymmetric: `maxSurge` rounds **up**, `maxUnavailable` rounds **down**. So at 10 replicas with 25 percent you surge by 3 and can lose 2.

**For a service that must not lose capacity: `maxUnavailable: 0`** with `maxSurge` at 25 percent or an absolute number. This means a new pod must be Ready before an old one is terminated, so served capacity never drops below the declared replica count. It costs cluster headroom - during the rollout you need room for 12-13 pods - and it is slower, because each step waits for readiness.

Two caveats worth stating: `maxUnavailable: 0` **deadlocks** if the cluster cannot schedule the surge pods, so it needs autoscaling or headroom to be reliable. And `maxUnavailable: 0` with `replicas: 1` requires at least two pods' worth of capacity, which is why single-replica deployments cannot be zero-downtime.

### Q86. Successful rollout, broken service `[T]`

Kubernetes reports success when its own criterion is met - all pods from the new ReplicaSet are Ready - and *Ready* is whatever your readiness probe says it is.

1. **The readiness probe is meaningless.** A probe on `/` or on a static endpoint that returns 200 as soon as the servlet container is up says nothing about whether the application can serve requests. If the probe does not exercise the code path that broke, the rollout is green by construction. This is the most common case by a wide margin.
2. **`minReadySeconds: 0` with a probe that passes before failure.** The pod passes readiness at 20 seconds, the rollout proceeds, and the pod fails at 60 seconds when the first real request arrives or the first scheduled task runs. The Deployment has already declared success and deleted the old ReplicaSet's pods.
3. **The failure is not in the pod at all.** A configuration error pointing at the wrong downstream, a missing database migration, a broken API contract with a caller, an expired credential. Every pod is genuinely healthy and the *system* is broken.
4. **The failure is a subset of traffic.** A specific endpoint, a specific tenant, a specific payload shape. Aggregate probe health and even aggregate error rate can stay green while a customer is completely broken.

The lesson: Kubernetes verifies *liveness of your process*, not *correctness of your service*. Rollout success must be gated on **service-level signals** - error rate and latency compared against the pre-rollout baseline - which is exactly what a canary controller (Q137) does and what a plain Deployment cannot.

### Q87. Readiness, liveness and startup probes

| Probe | On failure | Purpose |
| --- | --- | --- |
| **Readiness** | The pod is removed from Service endpoints. The container keeps running. Recoverable - it rejoins when the probe passes. | "Can I serve traffic right now?" |
| **Liveness** | The **container is killed** and restarted per the restart policy. | "Is this process wedged beyond recovery?" |
| **Startup** | The container is killed. While it is *running*, liveness and readiness probes are **suspended**. | "Has this slow-starting process finished starting?" |

**Conflating readiness and liveness** - typically by pointing the liveness probe at the same endpoint as readiness, or by making the readiness probe check dependencies and then reusing it for liveness - causes this failure: a downstream dependency blips, the probe fails, and instead of the pod merely leaving the load balancer for a few seconds, **every pod is killed and restarted simultaneously**. You have converted a partial, recoverable degradation into a full outage, and the restarts destroy connection pools and warm caches, making recovery slower than the original problem.

The rule: **readiness may check dependencies; liveness must not.** Liveness should check only that this process is capable of making progress - typically a trivial endpoint that proves the request-handling thread pool is not deadlocked. If the answer to a failure is "restarting will not help", it does not belong in a liveness probe.

### Q88. Liveness restart loop on a slow JVM `[T]`

**The feedback loop:**

1. Traffic is high, so the JVM is under GC and CPU pressure and the request path is slow.
2. The liveness probe has a timeout of 1 second and `failureThreshold: 3`. Under load, the probe endpoint - served by the same thread pool as real traffic - takes longer than 1 second.
3. Three consecutive failures, and kubelet kills the container.
4. The pod restarts. It now has a cold JVM: no JIT compilation, cold caches, an empty connection pool, and it must re-establish downstream connections. Start-up itself consumes CPU.
5. Meanwhile its share of the traffic redistributes to the remaining pods, pushing *them* further into the same condition.
6. The restarted pod is slow, fails its probe again, and is killed again. More pods enter the loop. The service collapses under a load it was previously handling.

This is a metastable failure: removing the original load spike does not fix it, because the restarts are now generating the pressure.

**Two fixes:**

1. **Use a startup probe.** `startupProbe` with a generous `failureThreshold × periodSeconds` budget (say 5 minutes) suspends liveness entirely until the application has started. This is the correct fix for the start-up half and is what the probe exists for.
2. **Make the liveness probe cheap and independent of load.** Point it at a dedicated endpoint served off the main thread pool (Spring Boot's `/actuator/health/liveness` group with no dependency indicators), raise `timeoutSeconds` to 5-10 and `failureThreshold` to 5-6, and remove anything from it that can be slow under load. The right liveness probe answers "is this JVM deadlocked", and the answer to that is either instant or never.

The broader fix is to size the pod so it is not saturated, and to shed load (Q110 in `03-microservices`) rather than let latency grow unbounded.

### Q89. Pod lifecycle and graceful shutdown

The exact sequence after `DELETE`:

1. The API server sets `deletionTimestamp` on the pod and `deletionGracePeriodSeconds`. The pod object is not removed.
2. **Two things now happen in parallel, with no ordering guarantee between them.** This is the whole problem.
   - **(a)** The **endpoint path**: the EndpointSlice controller observes the terminating pod and removes it (or marks it `terminating` with `serving: true`) from the EndpointSlice. That change propagates to every kube-proxy / dataplane on every node, and to any ingress controller or mesh watching endpoints, each of which then reprograms its rules. This takes anywhere from tens of milliseconds to several seconds.
   - **(b)** The **kubelet path**: kubelet sees the deletion, runs the `preStop` hook to completion (it is synchronous and blocking), then sends **`SIGTERM`** to PID 1 of each container.
3. The application handles `SIGTERM`: stops accepting new connections, finishes in-flight requests, drains message consumers, closes pools, exits.
4. If the container has not exited when `terminationGracePeriodSeconds` elapses **from step 2** (the `preStop` hook's duration is *inside* this budget, not additional), kubelet sends **`SIGKILL`**.
5. Once all containers are gone, kubelet reports it, and the API server removes the pod object.

Key details interviewers probe: `preStop` runs **before** `SIGTERM`, not after; the grace period includes the `preStop` hook; and there is **no guarantee that endpoint removal completes before `SIGTERM` is sent**.

### Q90. Connection resets despite graceful shutdown `[T]`

**The race** is step 2 above. Endpoint removal (2a) is asynchronous and involves at least four hops - EndpointSlice controller → API server → every kube-proxy → every node's iptables/IPVS/eBPF tables - plus the ingress controller and any mesh sidecar, each with its own watch latency and reprogramming cost. `SIGTERM` (2b) is a local operation on one node and completes in microseconds.

So the ordinary case is: the application receives `SIGTERM`, closes its listener, and *then* a node whose forwarding rules have not yet been updated sends it a connection. The client gets a connection refused or a reset. With HTTP keep-alive it is worse - the client holds an established connection to a socket the server is closing, so an in-flight request fails mid-flight.

**Closing it:**

1. **A `preStop` sleep.** `preStop: exec: ["sleep", "10"]` (or `sleep` via the `httpGet` alternative if there is no shell - distroless needs the `SLEEP` action or a tiny binary). This is the standard fix and it is not a hack: the pod is removed from endpoints at the start of step 2, and the sleep delays `SIGTERM` long enough for propagation to complete everywhere. The application keeps serving normally during the sleep.
2. **Fail readiness first, then delete.** If you control the sequence, mark the pod not-ready and wait before issuing the delete. Spring Boot's `server.shutdown=graceful` plus `management.endpoint.health.probes.enabled` and the `AvailabilityChangeEvent` for `ReadinessState.REFUSING_TRAFFIC` does this from inside the application.
3. **Set `terminationGracePeriodSeconds` longer than the `preStop` sleep plus the longest in-flight request**, or you have simply moved the `SIGKILL` earlier.
4. **Client-side**: retries on idempotent requests, and connection-pool settings that do not hold a connection past the server's keep-alive timeout. This is the only fix that also covers node failure, where no graceful path exists at all.

The number for the sleep should be measured - watch how long endpoint propagation actually takes in your cluster - but 5-15 seconds is typical.

*Hook: an endpoint-propagation race you found in production and the number you settled on.*

### Q91. Requests, limits and QoS

- **Request** - what the scheduler reserves. It is the only number the scheduler uses to decide fit, and it is the number that determines CPU shares (relative weight under contention).
- **Limit** - the hard ceiling enforced by the kernel. CPU limits become CFS quota (throttling); memory limits become `memory.max` (OOM kill).

The three QoS classes, derived automatically:

| Class | Condition | Eviction order |
| --- | --- | --- |
| **Guaranteed** | Every container has requests == limits for both CPU and memory | Evicted **last** |
| **Burstable** | At least one request set, but not all equal to limits | Middle; within Burstable, pods using the most memory *relative to their request* go first |
| **BestEffort** | No requests or limits at all | Evicted **first** |

**For a Java service** this matters in a specific way. Guaranteed QoS gives you the best eviction protection and, on a node with a static CPU manager policy, exclusive CPUs - which removes CFS throttling noise entirely and is genuinely valuable for latency-sensitive JVM workloads. But requests == limits for CPU means you cannot burst, and a JVM's CPU profile is extremely bursty (GC, JIT, start-up).

The configuration I default to is **memory request == memory limit** (so the JVM's footprint is honest, the pod is protected from memory-pressure eviction, and `MaxRAMPercentage` computes against a stable number) with **a CPU request sized to steady-state and no CPU limit** - which is Burstable, and which is Q93.

### Q92. CPU limit made p99 worse `[T]`

Utilization dropped *because* latency got worse: the pod is spending time descheduled, and descheduled time is not counted as utilization.

The mechanism is CFS throttling (Q76). The limit becomes a quota per 100 ms period. When the pod's threads collectively exhaust the quota, **all of them are frozen until the period rolls over** - up to 100 ms of dead time. The JVM makes this acute because its CPU usage is spiky rather than smooth:

- A **G1 young collection** runs on `ParallelGCThreads` threads simultaneously. A 5 ms collection on 8 threads is 40 ms of quota - nearly half a period on a 1-core limit - so the collection itself gets throttled and the stop-the-world pause stretches to tens or hundreds of milliseconds. The GC log signature is `real` time far exceeding `user + sys`.
- **JIT compilation** competes for the same quota during warm-up.
- Any burst of concurrent requests multiplies thread-level CPU demand for a few milliseconds.

So average utilization is low - the pod is idle most of the time - but every burst hits the quota wall, and the burst is exactly when requests are being served. p99 is composed almost entirely of throttled periods.

The diagnostic is the cgroup's `cpu.stat`: `nr_throttled` and `throttled_time`, exposed as `container_cpu_cfs_throttled_seconds_total` in cAdvisor. Any non-trivial throttling on a latency-sensitive service is the answer. (There was also a well-known CFS bandwidth accounting bug fixed in kernel 5.4 that caused throttling far below the quota; worth knowing, less relevant on modern kernels.)

### Q93. Do you set CPU limits?

**My position: no CPU limit for latency-sensitive services; a correctly sized CPU request instead. Always a memory limit.**

The mechanism behind it: CPU is a **compressible** resource. Without a limit, a pod that wants more CPU than its request gets it *if the node has spare capacity*, and if it does not, the CFS scheduler allocates proportionally to requests. So the request already provides fair sharing under contention - which is the protection people think the limit is providing. The limit adds nothing except throttling during bursts the node could have absorbed for free.

Memory is **incompressible** - there is no "share it out" - so a memory limit is mandatory or one leaking pod takes the node down.

**Where I would set a CPU limit:**

- **Multi-tenant clusters** where a hostile or unknown workload could starve neighbours, and the request-based fair share is not a sufficient guarantee. This is the main legitimate case.
- **Batch and best-effort workloads** running alongside latency-sensitive ones, where you explicitly want to cap the batch job.
- **Cost governance** where predictable per-pod cost matters more than tail latency.
- **When the team cannot be trusted to set sane requests**, in which case the limit is a blunt instrument standing in for a missing process.

The honest caveat: no CPU limits means node capacity planning has to be real, because a node's actual usage can exceed the sum of requests. You need node-level CPU pressure monitoring and enough headroom, and you need `LimitRange` defaults so that nobody ships a pod with no request at all.

*Hook: removing CPU limits from a latency-sensitive service and the p99 change you measured.*

### Q94. Eviction, OOMKill and preemption

| | Who | Trigger | Symptom |
| --- | --- | --- | --- |
| **Node-pressure eviction** | **kubelet** | Node-level resource pressure crosses a threshold: `memory.available`, `nodefs.available`, `imagefs.available`, `pid.available` | Pod status `Failed`, reason **`Evicted`**, message naming the pressure signal. Pod object remains for inspection. |
| **OOMKill** | **The kernel** | A container exceeds its cgroup `memory.max` | Container status `terminated`, reason **`OOMKilled`**, exit code **137**. The pod restarts per its restart policy; the pod object is unchanged. |
| **Preemption** | **The scheduler** | A higher-`priorityClass` pod cannot be scheduled anywhere | Victim pods deleted with an event `Preempted`; the pending pod's events name the preemption. |

Telling them apart from the pod status:

- `kubectl get pod` showing `Evicted` with `kubectl describe` naming a pressure signal → kubelet, node-level. The node was short of memory or disk; the pod may not have been over its own limit at all. Look at the node.
- `kubectl describe pod` showing `Last State: Terminated, Reason: OOMKilled, Exit Code: 137` → kernel, container-level. This container exceeded *its own* limit. Look at the application (Q75).
- Restart count increasing with `OOMKilled` and no node events → a leak or an under-sized limit.
- Pod suddenly `Terminating` with a preemption event and a lower priority class than a newly-scheduled pod → scheduler.

The subtlety worth naming: a container can be OOMKilled while the *node* has plenty of free memory (its own limit was exceeded), and a pod can be evicted while it is well under its own limit (the node was under pressure and it was the best victim). Conflating these sends you debugging the wrong layer.

### Q95. StatefulSet versus Deployment

A StatefulSet adds four guarantees:

1. **Stable network identity.** Each pod gets an ordinal name (`web-0`, `web-1`) and, with a headless Service, a stable DNS record that survives rescheduling.
2. **Stable storage.** Each pod gets its own PVC from `volumeClaimTemplates`, and the same pod ordinal always gets the same PVC - across restarts and rescheduling.
3. **Ordered, sequential creation and deletion.** Pods are created 0, 1, 2 and each waits for the previous to be Running and Ready; deletion is the reverse. (Relaxable with `podManagementPolicy: Parallel`.)
4. **Ordered rolling updates**, highest ordinal first, one at a time, each waiting for Ready.

**What it costs during a rolling update:** it is strictly serial. Ten replicas means ten sequential restarts, each waiting for full readiness - so a rollout that takes 30 seconds for a Deployment takes 5-10 minutes. There is no `maxSurge`: a StatefulSet pod cannot be surged, because the new pod would need the same identity and the same volume. So `maxUnavailable` is effectively 1, and **capacity dips by one replica for the whole rollout**.

Worse, a **stuck pod blocks the entire rollout**. If `web-7` fails to become Ready, the update stops there and `web-6` through `web-0` are never updated. That is the intended safety property (do not break the whole cluster) and it is also the thing that leaves you half-rolled-out at 3 am. `partition` in the update strategy is the escape hatch, and `podManagementPolicy: Parallel` plus careful ordering is the pragmatic setting for stateful systems that do their own quorum management.

### Q96. DaemonSet, Job and CronJob

- **DaemonSet** - one pod per node (matching a selector). For node-level agents: log shipper, metrics agent, CNI, CSI node plugin, security agent. Scales with the cluster automatically; tolerates node taints by default for system-critical ones.
- **Job** - runs pods to successful completion. `completions` and `parallelism` control how many; `backoffLimit` bounds retries; `activeDeadlineSeconds` bounds total runtime.
- **CronJob** - creates Jobs on a schedule.

**Settings you must set on a CronJob:**

| Field | Default | Why the default is a trap |
| --- | --- | --- |
| `concurrencyPolicy` | **`Allow`** | Two runs overlap if one is slow, and most batch jobs are not safe to run concurrently. Set `Forbid` (skip) or `Replace` (kill the old one) deliberately. |
| `startingDeadlineSeconds` | unset | If the controller is down past a missed schedule, behaviour is surprising: after 100 missed schedules with no deadline, the CronJob **stops scheduling entirely** and logs an error. Set it to something bounded (e.g. 200s). |
| `successfulJobsHistoryLimit` / `failedJobsHistoryLimit` | 3 / 1 | Fine, but if you raise them you accumulate Job and Pod objects and pressure etcd. |
| `activeDeadlineSeconds` (on the Job template) | unset | A hung job runs forever, holding resources and blocking `Forbid`. |
| `backoffLimit` | 6 | Six retries with exponential backoff on a job that is deterministically broken wastes 10+ minutes and obscures the failure. |
| `suspend` | false | The operational off-switch. Know it exists before the incident. |

The other trap: **CronJob schedules are in the controller's time zone** (UTC) unless you set `timeZone` (stable since 1.27), and a lot of incidents come from a job that ran an hour early after a DST change.

### Q97. Scheduling controls, and surviving an AZ loss

- **`nodeSelector`** - simple equality match on node labels. Hard requirement, no expressiveness.
- **Node affinity** - `requiredDuringScheduling` (hard) and `preferredDuringScheduling` (soft, weighted). Set operators, negation, multiple terms.
- **Pod affinity / anti-affinity** - schedule near or away from other pods, with a `topologyKey` defining "near". Anti-affinity is the classic "spread my replicas".
- **Taints and tolerations** - the *node* repels pods (`NoSchedule`, `PreferNoSchedule`, `NoExecute`) unless the pod tolerates it. This is how you reserve a node pool.
- **Topology spread constraints** - declare a maximum skew across a topology domain, with `whenUnsatisfiable: DoNotSchedule` or `ScheduleAnyway`.

**To survive an AZ loss, use topology spread constraints**, not pod anti-affinity:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels: { app: orders }
```

Why not anti-affinity: `requiredDuringScheduling` pod anti-affinity on a zone topology key is all-or-nothing - it can only express "at most one pod per zone", so with 3 zones you cannot run more than 3 replicas, and with `preferred` it gives you no control over how uneven the spread gets. Topology spread expresses the actual requirement - "no zone has more than one more replica than any other" - and scales to any replica count.

`ScheduleAnyway` versus `DoNotSchedule` is the important choice: `DoNotSchedule` gives you a strict guarantee and leaves pods `Pending` when a zone is unavailable, which during an AZ outage is exactly the wrong behaviour. I use `ScheduleAnyway` for availability spreading and `DoNotSchedule` only when unevenness is genuinely unacceptable.

Node-level spread (`kubernetes.io/hostname`) should be layered on top, because an AZ-spread deployment with all three zone-replicas on one node per zone still loses a third of capacity to a single node failure.

### Q98. Pending pod with free CPU `[T]`

`kubectl describe pod` and read the scheduler's events first - it says exactly which predicate failed and for how many nodes. Then, in the order I would check:

1. **Memory, not CPU.** "Plenty of free CPU" says nothing about memory, and memory is the more common binding constraint. `Insufficient memory`.
2. **The request is larger than any single node.** A pod requesting 8 CPU on 4-CPU nodes never schedules regardless of cluster-wide free capacity. Free capacity is not fungible across nodes.
3. **Taints without tolerations.** A dedicated node pool, a `NoSchedule` taint from an upgrade or from a node condition (`node.kubernetes.io/disk-pressure`, `not-ready`). `node(s) had untolerated taint`.
4. **Node affinity / selector mismatch.** The pod requires a label (instance type, architecture, zone) that no ready node has. Very common after a node group change.
5. **Topology spread or pod anti-affinity cannot be satisfied.** `DoNotSchedule` with all valid zones already at max skew.
6. **Volume topology.** The pod's PVC is bound to an EBS volume in zone `a`; the only nodes with capacity are in zone `b`. `node(s) had volume node affinity conflict`. This is the one people miss.
7. **ResourceQuota or LimitRange** on the namespace rejecting the pod - though this usually fails at admission with a clear error rather than leaving it Pending.
8. **No nodes at all in a usable state** - cluster autoscaler at max size, a node group that cannot launch instances (capacity error, quota, subnet IPs exhausted). Check the autoscaler's events and logs.
9. **Pod-level constraints**: `hostPort` conflicts, `PriorityClass` with preemption disabled, extended resources (GPU) unavailable.
10. **The scheduler itself** - not running, or the pod has a `schedulerName` pointing at a scheduler that does not exist.

### Q99. Six low-traffic services on Kubernetes `[A]`

**My default answer is no**, and the reasoning is total cost of ownership rather than technical merit.

Kubernetes' value is roughly proportional to the number of workloads and teams sharing the platform. It buys bin-packing across many services, a uniform deployment interface, self-healing, and a rich ecosystem. At six low-traffic services, the bin-packing saves almost nothing, one team can hold six deployment scripts in their head, and the ecosystem is overhead rather than leverage.

The costs are not proportional and they are permanent: cluster upgrades every few months, node AMI patching, CNI and CSI version compatibility, RBAC, admission policy, the control plane bill, an ingress controller, a certificate manager, and a Prometheus stack. That is a part-time platform engineer's job forever, for six services.

**Alternatives, in the order I would consider them:**

1. **ECS on Fargate** (or Cloud Run / Container Apps). Containers, rolling deployments, autoscaling, health checks, service discovery and load balancer integration, with no cluster to operate. This covers the six-service case almost exactly and is my usual recommendation.
2. **App Runner / Elastic Beanstalk** if the services are plain HTTP applications and the team wants even less.
3. **Lambda** if the traffic is genuinely spiky or low enough that scale-to-zero dominates the economics, and the workload fits the model.
4. **Plain EC2 with an ASG and a deployment pipeline** if the constraint is skills rather than scale - it is unfashionable and it works.
5. **A managed Kubernetes cluster shared with another team**, if one exists. Most of the cost is the cluster, not the workloads.

**What would change my answer:** the organization already runs Kubernetes and has the platform capability, in which case the marginal cost of six more services is near zero and consistency wins. Or the six services are the first six of forty. Or there is a hard requirement Kubernetes uniquely satisfies - a specific operator, a stateful system with a mature operator, strict scheduling requirements, or portability across clouds as a genuine commercial constraint rather than an aspiration.

*Hook: a platform choice you made against the fashionable answer, and how it aged.*

---

## 7. Kubernetes networking, storage and cluster operations

### Q100. The networking model and CNI

The model has three rules:

1. Every pod gets its **own IP address** in a flat address space.
2. **Every pod can reach every other pod directly by IP, without NAT**, regardless of node.
3. Agents on a node (kubelet, system daemons) can reach all pods on that node.

The flat requirement matters because it removes port mapping entirely: a pod sees the same IP and port that other pods use to reach it, so applications, service discovery and observability tooling all see one consistent address. It is why Kubernetes networking is simpler to reason about than Docker's default bridge networking, and it is also the reason IP address management becomes a real constraint at scale (see the AWS VPC CNI's ENI limits).

**A CNI plugin must provide:**

- **IPAM** - allocate and release a pod IP from a pool.
- **Interface setup** - create the veth pair (or equivalent), move one end into the pod's network namespace, configure the address, routes and MTU.
- **Reachability** - ensure packets to any pod IP reach the right node, whether by native VPC routing (AWS VPC CNI), an overlay (VXLAN or Geneve, as in Flannel or Calico's overlay mode), or BGP-advertised routes (Calico native).
- **Teardown** on pod deletion.

Optionally but commonly: NetworkPolicy enforcement (Calico, Cilium - Flannel does not, which surprises people), and increasingly the Service dataplane itself (Cilium replacing kube-proxy).

### Q101. How a ClusterIP Service routes

A ClusterIP is a **virtual IP that nothing listens on**. There is no proxy process in the path; the IP exists only as a set of packet-rewriting rules on every node.

- **iptables mode** (the long-standing default): kube-proxy writes a chain per Service that matches the ClusterIP and port, then a chain per endpoint with a `statistic --mode random --probability` rule to pick one, then a DNAT rule rewriting the destination to the pod IP. Connection tracking (conntrack) keeps subsequent packets of the flow going to the same pod. Selection is **random per connection**, not round-robin.
  - **Cost**: rules are evaluated as a linear chain, so lookup is O(n) in the number of Services, and *updating* the rules requires rewriting and reloading large rule sets. At a few thousand Services this becomes seconds of CPU per update and visible endpoint propagation delay.
- **IPVS mode**: kube-proxy programs the kernel's IPVS load balancer instead. Lookup is a hash table, so **O(1)**, and updates are incremental. It also offers real algorithms - round-robin, least-connection, source hashing - rather than random. It still uses iptables for a few things (masquerade, NodePort), so it is not a full replacement.
- **eBPF dataplanes** (Cilium, Calico eBPF): replace kube-proxy entirely. Service resolution happens in an eBPF program attached at the socket or TC layer, using BPF maps for O(1) lookup. Because it can act at `connect()` time, it rewrites the destination *before* the packet is created, avoiding NAT and conntrack overhead entirely for pod-to-Service traffic. It also removes the conntrack table as a scaling limit and gives much faster endpoint propagation.

The practical summary: iptables is fine to a few hundred Services, IPVS to a few thousand, eBPF beyond that and for latency-sensitive workloads.

### Q102. Service, Endpoints and EndpointSlice

- **Service** - the stable identity: a ClusterIP, a port mapping, and a label selector.
- **Endpoints** (the original object) - **one object per Service** listing every ready pod IP and port.
- **EndpointSlice** - the same information sharded into multiple objects, each holding up to 100 endpoints by default, with richer per-endpoint fields (topology hints, `ready`/`serving`/`terminating` conditions, node name).

**Why EndpointSlice was introduced**, and what breaks without it: the Endpoints object is a single resource containing the full list. With a Service backing 5,000 pods, every pod change rewrites and re-transmits the *entire* object - hundreds of kilobytes - to every watcher: every kube-proxy on every node, the ingress controller, the mesh control plane. During a rolling update of that Service, you get thousands of full-object updates. The effects are:

- **API server and etcd load** proportional to endpoints × nodes × churn, which at scale saturates the control plane.
- **Endpoint propagation latency** growing into tens of seconds, which directly worsens the Q90 shutdown race and makes rollouts drop traffic.
- **A hard ceiling** around the object size limit (etcd's 1.5 MB default), roughly 5,000 endpoints per Service.

EndpointSlice makes an update touch one slice of ~100 endpoints, so transmitted bytes drop by roughly the sharding factor. It also enables **topology-aware routing** (`trafficDistribution: PreferClose` / the older `service.kubernetes.io/topology-mode` hints), because per-endpoint zone information now exists - which is a direct cross-AZ data transfer cost saving (Q256).

### Q103. Pod removed from a Service still receiving traffic `[T]`

The full propagation path, and the lag at each hop:

1. **Pod becomes not-ready or is deleted.** kubelet updates the pod status → API server. *Lag: the readiness probe's `periodSeconds` × `failureThreshold` if it is a probe failure - often 10-30 seconds and entirely under your control.*
2. **EndpointSlice controller** watches pods, recomputes the slice, writes it. *Lag: watch delivery plus the controller's batching, typically tens to hundreds of milliseconds; much worse under control-plane load.*
3. **API server persists and fans out the watch event** to every watcher. *Lag: proportional to the number of watchers and object size - this is the hop EndpointSlice was created to fix.*
4. **kube-proxy on every node** receives it and reprograms the dataplane. *Lag: iptables mode has to render and `iptables-restore` the ruleset, which with thousands of Services is seconds; IPVS and eBPF are incremental and fast. kube-proxy also has a `minSyncPeriod` that deliberately batches.*
5. **Ingress controller** (NGINX, ALB controller, Envoy) has its own watch and its own reload/config-push. *Lag: NGINX reloads, the AWS Load Balancer Controller calls the AWS API and waits for target deregistration - **which has its own deregistration delay, defaulting to 300 seconds**. This is by far the biggest one and it lives outside Kubernetes.*
6. **Service mesh control plane** (istiod) recomputes and pushes to every sidecar. *Lag: push batching plus xDS delivery, typically sub-second but load-dependent.*
7. **Existing connections.** Even after every rule is updated, **conntrack keeps established flows pinned to the old pod**, and HTTP keep-alive means clients hold open connections. Rules only affect *new* connections.
8. **Client-side caches** - a client-side load balancer (Spring Cloud LoadBalancer, gRPC's built-in), or DNS caching in the JVM (Q105), holds stale endpoints independently of all of the above.

Point 7 is the one that explains "several seconds" most often, and it is why `preStop` sleeps and connection draining exist rather than trying to make propagation instant.

### Q104. Headless services and DNS

A headless Service is `clusterIP: None`. No virtual IP is allocated, no dataplane rules are programmed, and DNS behaves differently.

- **Normal Service**: `my-svc.ns.svc.cluster.local` resolves to **one A record - the ClusterIP**. Load balancing happens in the dataplane.
- **Headless Service**: the same name resolves to **an A record per ready pod IP**. With a StatefulSet, each pod also gets `pod-0.my-svc.ns.svc.cluster.local` resolving to that specific pod.

```
$ dig +short my-svc.default.svc.cluster.local
10.1.2.7
10.1.4.19
10.1.9.3
```

You need one when:

- **The client does its own load balancing** and wants the endpoint list - gRPC with a DNS resolver, a Kafka or Cassandra client, a mesh-less client-side balancer.
- **Individual pods must be addressable** - StatefulSet members forming a cluster (etcd, Elasticsearch, Kafka), where each node needs a stable name for peers.
- **Long-lived connections with per-connection balancing would be wrong** - HTTP/2 and gRPC multiplex everything over one connection, so a ClusterIP pins all traffic to one pod for the connection's lifetime. Headless plus client-side balancing is the standard fix (the alternative is a mesh).

The caveat: DNS-based endpoint discovery inherits every DNS caching problem (Q105 and `03-microservices` Q122), and the record set is capped by UDP response size before falling back to TCP.

### Q105. CoreDNS at scale

**`ndots`** is the crux. Kubernetes injects into every pod:

```
search my-ns.svc.cluster.local svc.cluster.local cluster.local eu-west-1.compute.internal
options ndots:5
```

`ndots:5` means: if a name has **fewer than 5 dots**, try it with each search domain *first* before trying it as an absolute name. `api.example.com` has 2 dots, so the resolver issues:

1. `api.example.com.my-ns.svc.cluster.local` → NXDOMAIN
2. `api.example.com.svc.cluster.local` → NXDOMAIN
3. `api.example.com.cluster.local` → NXDOMAIN
4. `api.example.com.eu-west-1.compute.internal` → NXDOMAIN
5. `api.example.com` → answer

That is **5 queries** for one external lookup - and glibc's resolver sends A and AAAA in parallel, so it is really **10 packets**. At scale this is the dominant load on CoreDNS and the source of the classic intermittent 5-second DNS timeout (a kernel conntrack race on parallel DNS via the same source port, mitigated by `single-request-reopen` or by NodeLocal DNSCache).

**What I configure:**

1. **`dnsConfig` with `ndots: 2`** on pods that mostly call external names, or - better - **use fully-qualified names with a trailing dot** (`api.example.com.`) which bypasses the search list entirely.
2. **NodeLocal DNSCache** - a DaemonSet caching resolver on every node, so pods query `169.254.20.10` locally over a link-local address. This eliminates most cross-node DNS traffic, caches negative responses, and uses TCP upstream which sidesteps the conntrack race. This is the single highest-value change.
3. **`autopath`** in CoreDNS, which collapses the search-domain walk server-side into one query.
4. **Scale CoreDNS** with the cluster-proportional autoscaler, and give it CPU headroom - DNS failures under load look like application failures everywhere at once.
5. **Cache negative responses** and tune the `cache` plugin's TTLs.
6. **In the JVM specifically**: `networkaddress.cache.ttl` - the default with a security manager is to cache successful lookups **forever**, which means a JVM can hold a dead pod IP indefinitely. Set it to 30-60 seconds.

### Q106. Ingress, Gateway API and service mesh

| | Solves |
| --- | --- |
| **Ingress** | North-south HTTP routing into the cluster: host and path matching to a Service, TLS termination. One resource, one persona. |
| **Gateway API** | The same, plus richer routing (header/query/method matching, weighted traffic splitting, request mirroring, header modification) with **role-oriented resource separation**: `GatewayClass` (infrastructure provider), `Gateway` (cluster operator), `HTTPRoute` (application team). Also covers TCP, gRPC and, via GAMMA, east-west mesh traffic. |
| **Service mesh** | East-west concerns between services: mTLS, retries, timeouts, circuit breaking, fine-grained traffic shifting, and uniform L7 telemetry - all without changing application code. |

**The migration reason from Ingress to Gateway API** is that Ingress's spec is too small for what people need, so every controller extended it with **annotations**. The result is that an Ingress manifest is not portable, the annotations are unvalidated strings, and there is no schema to review or lint. Rewrites, timeouts, canary weights, auth and rate limits are all vendor-specific annotation soup.

Gateway API fixes this structurally: those behaviours are **typed, validated API fields**, so they can be reviewed, policy-checked and moved between implementations. Equally important is the **role separation** - the platform team owns the `Gateway` (listeners, TLS certificates, IP allocation) and delegates route attachment to namespaces, so an application team can publish a route without being able to change the listener or hijack another team's hostname. With Ingress, every team needs write access to objects that can conflict with each other.

Gateway API reached GA for the core resources in 2023 and is the direction of travel; Ingress is frozen. I would use Gateway API for new clusters and migrate existing ones when the annotation sprawl becomes a real cost.

### Q107. NetworkPolicy

A NetworkPolicy selects pods and declares allowed traffic. The critical semantics:

- Policies are **additive and allow-only**. There is no deny rule; the union of all matching policies is the allow set.
- A pod with **no** policy selecting it allows all traffic. A pod with **any** policy selecting it for a direction (`Ingress` or `Egress`) denies everything in that direction except what is explicitly allowed.
- Therefore **default-deny is itself a policy** - an empty-selector policy with `policyTypes: [Ingress, Egress]` and no rules - and it must be applied per namespace.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: payments }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

**What NetworkPolicy cannot express:**

- **L7 anything** - HTTP methods, paths, headers, gRPC services. It is L3/L4 only.
- **Identity beyond labels and IP blocks.** No workload identity, no cryptographic authentication - a pod that can spoof a label selector's target is indistinguishable.
- **Egress to a DNS name.** `ipBlock` only, so allowing `api.stripe.com` means allowing a CIDR that changes. (Cilium and Calico add DNS-aware egress policy as CRDs; that is not NetworkPolicy.)
- **Cluster-wide default policy.** It is namespaced, so you need one per namespace - hence `AdminNetworkPolicy` (newer) and vendor CRDs.
- **Egress from the node**, or traffic that does not traverse the pod network.

**What enforces it:** the CNI plugin, not Kubernetes. Calico, Cilium, Antrea and the AWS VPC CNI (with the network policy agent enabled) implement it; **Flannel alone does not**, so on a Flannel cluster NetworkPolicy objects are accepted by the API server and silently do nothing. That is a genuinely dangerous failure mode and worth calling out - always verify enforcement with a test pod rather than assuming.

### Q108. Service mesh data plane cost

The sidecar (Envoy) intercepts traffic via iptables rules installed by an init container, redirecting all inbound and outbound TCP traffic through the proxy's ports. It therefore sees **every TCP connection into and out of the pod**, terminating and re-originating them - which is how it can do mTLS, L7 routing, retries and telemetry without application changes. It does *not* see traffic that bypasses the redirect: `hostNetwork` pods, excluded ports and CIDRs, and (in most configurations) UDP.

**Budget, per hop:**

- **Latency**: 2-5 ms added p99 per hop in a well-tuned mesh - roughly 0.5-1 ms per proxy traversal at p50, with the tail dominated by the proxy's worker-thread scheduling under load. Two proxies per hop (client sidecar and server sidecar), so a five-hop request accumulates real time. `03-microservices` Q130 covers where it comes from.
- **CPU**: ~0.1-0.5 vCPU per sidecar at moderate request rates; Envoy's cost scales with requests per second and with the amount of L7 processing (header manipulation, telemetry cardinality).
- **Memory**: 40-100 MB baseline, but the real driver is **configuration size** - by default every sidecar receives the full cluster's service configuration, so memory grows with the number of Services in the mesh. Scoping with `Sidecar` resources or `exportTo` is essential past a few hundred services.
- **Pod density**: doubling container count per pod affects scheduling and node capacity.

**Ambient / sidecarless** changes the model: an L4 node-level component (ztunnel, a DaemonSet) handles mTLS and identity for all pods on the node, and L7 processing moves to an optional per-namespace **waypoint proxy** that you opt into only where you need retries, routing or L7 policy. The effects:

- **Cost becomes proportional to the node count and to actual L7 use**, not to pod count. For an estate that mostly wants mTLS and telemetry, this is a large saving.
- **No sidecar injection**, so no pod restarts to enrol, no race between the sidecar and the application at start-up, and no `preStop` ordering problems - all of which are real operational papercuts.
- **The trade-off**: the L4/L7 split is a new concept to reason about, the node-level component is a shared blast radius, and per-pod resource attribution becomes harder.

### Q109. mTLS in a mesh

**Where the certificates come from**: the mesh control plane acts as (or fronts) a CA. In Istio, `istiod` runs a CA; each proxy generates a key pair on start-up and sends a CSR to `istiod` over a channel authenticated by the pod's **projected ServiceAccount token** (an audience-bound, short-lived JWT the API server issues and the kubelet mounts). `istiod` validates the token with the API server's TokenReview, derives the workload's **SPIFFE identity** (`spiffe://cluster.local/ns/<ns>/sa/<serviceaccount>`) from it, and issues a certificate with that identity as a URI SAN. The root CA is either self-signed by `istiod`, or - properly - an intermediate issued by your organization's PKI or by cert-manager.

**Rotation period**: workload certificates are short-lived by design, **24 hours by default in Istio, often tuned to 1-12 hours**. The proxy's agent re-requests well before expiry (at ~50 percent of lifetime), so rotation is continuous and invisible. The root CA has a multi-year lifetime and rotating it is a deliberate, staged operation (distribute the new root to all trust bundles, then switch the signing key, then remove the old root - Q160 in `03-microservices`).

**During a control plane outage**: existing certificates remain valid until they expire, and existing connections and configuration keep working - the data plane is designed to fail static. So a 30-minute `istiod` outage is usually invisible. What breaks:

- **New pods cannot get a certificate**, so anything scheduled during the outage cannot join the mesh and will fail mTLS. Scale-out and rollouts are blocked.
- **No configuration updates** propagate - new Services, endpoint changes, routing changes. Sidecars keep their last-known-good config, so endpoint changes are the sharp edge: a pod that dies during the outage keeps receiving traffic.
- **If the outage outlasts the certificate lifetime**, workloads start failing mTLS as their certificates expire. With a 24-hour lifetime you have hours; with a 1-hour lifetime you have minutes. That is the argument against very short lifetimes without a highly available control plane.

### Q110. PV, PVC, StorageClass and access modes

- **PersistentVolume** - a cluster-scoped piece of storage, either pre-provisioned by an admin or created dynamically.
- **PersistentVolumeClaim** - a namespaced request for storage: size, access mode, StorageClass. Pods reference PVCs, never PVs.
- **StorageClass** - a named provisioning profile: which CSI driver, what parameters (volume type, IOPS, throughput, encryption key), the `reclaimPolicy` (`Delete` or `Retain`), whether volumes are expandable, and the `volumeBindingMode`.
- **Dynamic provisioning**: a PVC naming a StorageClass triggers the CSI external-provisioner to create real storage and a matching PV, then binds them.

**`volumeBindingMode` is the setting that matters most**: with `Immediate`, the volume is created as soon as the PVC exists - in whatever zone the provisioner picks - and the pod is then constrained to that zone, which routinely produces the "volume node affinity conflict" Pending pod (Q98). With **`WaitForFirstConsumer`**, binding is deferred until a pod is scheduled, so the scheduler picks the node first and the volume is created in the right zone. Use it always on a multi-AZ cluster.

**Access modes in practice on a cloud provider:**

| Mode | Meaning | Reality |
| --- | --- | --- |
| `ReadWriteOnce` (RWO) | Mountable read-write by a single **node** | EBS, GCP PD, Azure Disk. Note it is per *node*, not per pod - multiple pods on the same node can share it. This is what you actually get for block storage, and it means a pod cannot move to another node until the volume is detached (Q111). |
| `ReadWriteOncePod` (RWOP) | Single **pod**, strictly | Newer, and the correct choice when you need exclusivity (a database), because RWO does not give it. |
| `ReadWriteMany` (RWX) | Many nodes, read-write | Requires a shared filesystem: EFS, Azure Files, FSx, or NFS. Block storage cannot do this. Much higher latency and different consistency semantics than a local disk - and applications that assume POSIX semantics on EFS often behave badly. |
| `ReadOnlyMany` (ROX) | Many nodes, read-only | Rarely used. |

The trap: requesting RWX because "several pods need it" and then discovering the workload needed block-storage latency.

### Q111. StatefulSet pod stuck in ContainerCreating after node failure `[T]`

**The mechanism** is volume attachment, and specifically that a block volume can only be attached to one node at a time.

1. The node fails. The kubelet stops reporting, and after `node-monitor-grace-period` (40s default) the node controller marks it `NotReady`.
2. The **`VolumeAttachment` object still says the volume is attached to the dead node**, and the cloud provider's control plane agrees - because a failed node did not detach anything, and from EBS's point of view a healthy attachment exists.
3. Kubernetes will **not** force-detach until it is confident the old node will not write to it. For a StatefulSet, the pod itself is not even deleted automatically: the node controller adds a `node.kubernetes.io/unreachable` taint with `NoExecute`, which evicts most pods after `tolerationSeconds` (300s default) - but StatefulSet pods are only *marked* for deletion, and the StatefulSet controller will not create the replacement until the old pod object is **fully gone**, because two pods with the same identity and volume must never exist.
4. Once the pod is finally deleted, the new pod is scheduled, and the attach/detach controller must **detach from the old node** (which times out - the node is gone) before attaching to the new one. There is a further `maxWaitForUnmountDuration` (6 minutes by default in some versions) before force-detach.
5. Then the CSI driver attaches the volume to the new node (a cloud API call, tens of seconds), the kubelet mounts and formats-if-needed, and the container starts.

**How long**: typically **6-10 minutes end to end** with defaults, sometimes longer. The pod sits in `ContainerCreating` with `FailedAttachVolume` / `Multi-Attach error for volume` events for most of it.

**What you can do**: `Non-Graceful Node Shutdown` handling (add the `out-of-service` taint to a confirmed-dead node, which triggers immediate force-detach and pod deletion - this is the supported fast path, stable since 1.28); shorten the unreachable toleration; and, most importantly, **do not rely on this for availability** - a stateful system should have its own replication and quorum so that losing one member is not an outage, and the 8-minute reattach is a background repair rather than a customer-facing event.

### Q112. Cluster autoscaler, Karpenter and fixed node groups

| | Fixed node group | Cluster Autoscaler | Karpenter |
| --- | --- | --- | --- |
| **How it decides** | You decide | Simulates the scheduler against pending pods, scales a matching ASG/node group | Reads pending pods directly, computes an optimal instance shape, launches it via the cloud API |
| **Provisioning latency** | Zero (capacity is already there) | ASG scale-out plus node boot and registration: typically **2-4 minutes** | Direct EC2 launch, skipping the ASG: typically **40-90 seconds** |
| **Bin-packing** | Whatever you provisioned | Constrained to the instance types of pre-defined node groups; needs many groups to cover diverse shapes | Chooses from the full instance catalogue per batch of pending pods, so it fits the workload rather than the reverse |
| **Consolidation** | None | Scales down empty/under-utilized nodes against a group | Actively consolidates - replaces several under-used nodes with one cheaper node, and can replace on-demand with spot |
| **Cost behaviour** | Pay for peak, always | Better, but the node-group granularity leaves stranded capacity | Best; typically 20-50 percent lower for variable workloads |
| **Operational cost** | Lowest | Moderate; node group sprawl is the failure mode | Moderate; more churn, and churn is itself a risk |

**The trade-offs that matter beyond the table:**

- Karpenter's aggressive consolidation means **nodes are replaced frequently**, so workloads must genuinely tolerate disruption - correct PodDisruptionBudgets, graceful shutdown, and no assumption of node stability. A team that has never tested pod eviction will find out the hard way. `do-not-disrupt` annotations and consolidation policies are the controls.
- A **fixed node group is still the right answer** for a small, stable cluster, or as a floor of always-on capacity underneath an autoscaler - which is what I usually run: a small static baseline for system components, with Karpenter handling everything variable.
- **Neither autoscaler helps with the latency of a traffic spike** (Q114); they help with cost.

### Q113. HPA for a JVM service

The HPA controller polls metrics every 15 seconds and computes:

```
desiredReplicas = ceil(currentReplicas × (currentMetricValue / targetMetricValue))
```

with a tolerance (10 percent) below which it does nothing.

**What I scale on**: the metric that is *causally upstream of the user-visible symptom and linearly related to load*. For a request-driven JVM service, in order of preference:

1. **Requests per second per pod** (via `Pods` or `External` metrics from Prometheus Adapter or KEDA). Directly proportional to load, immediately responsive, and the target is derived from a load test.
2. **Concurrency / in-flight requests per pod**, which is Little's Law made operational and handles variable request cost better than RPS.
3. **Queue depth or consumer lag** for asynchronous workloads - this is the correct signal for a consumer and CPU is meaningless there.
4. **CPU**, as a fallback.

**The stabilization window** exists to prevent thrashing. `behavior.scaleDown.stabilizationWindowSeconds` (300s default) makes the controller take the *maximum* desired replica count over the trailing window before scaling down, so a brief dip in load does not remove capacity that is needed again in 30 seconds. Scale-up's default stabilization is 0 with a policy allowing rapid growth - asymmetric on purpose, because being slow to add capacity hurts users and being slow to remove it only costs money.

**Why CPU is often the wrong signal for a JVM:**

- **JIT and GC pollute it.** CPU spikes during warm-up and during collections without any change in served load, so the HPA scales up a pod that is merely compiling.
- **It is a lagging, indirect signal.** By the time CPU is at 70 percent, latency has usually already degraded, so you scale after the damage.
- **A JVM can be saturated at low CPU.** Blocking on a downstream call, a connection pool, or a lock produces high latency and low CPU - and the HPA scales *down*, precisely when you need more capacity. This is the failure mode that catches people.
- **Throttling distorts it** (Q92): a CPU-limited pod's utilization is measured against the limit and the throttled time is invisible.

### Q114. HPA and cluster autoscaler still drop requests `[T]`

Because the two autoscalers are **sequential**, and the total is far longer than either one's advertised latency. The timing chain for a spike at T=0:

| Step | Typical time |
| --- | --- |
| Metric is scraped by Prometheus / metrics-server | 15-30 s (scrape interval) |
| Metric becomes visible to the HPA (adapter query window, rate window) | 15-60 s |
| HPA control loop runs and computes a new replica count | 0-15 s |
| Deployment creates pods; scheduler finds no capacity → pods `Pending` | ~1 s |
| Cluster autoscaler / Karpenter notices pending pods | 10-30 s |
| Instance launch, boot, kubelet registration, node `Ready` | **40 s (Karpenter) to 4 min (ASG)** |
| Image pull on the fresh node | 10-60 s (much longer for a large image on a cold node) |
| Container start, JVM start-up, framework initialization | **20-60 s for Spring Boot** |
| Startup and readiness probes pass, `minReadySeconds` | 10-30 s |
| Endpoint propagation to the dataplane | 1-5 s |
| JVM warm-up before the pod serves at full speed | 30-120 s |

**Total: three to eight minutes** before the new capacity is genuinely useful. A traffic spike that doubles load in 60 seconds is over before the first new pod is warm.

**What actually fixes it:**

1. **Headroom.** Run at a utilization target that leaves room for the spike. This is the honest answer and it costs money.
2. **Overprovisioning pods** - low-priority placeholder pods that reserve node capacity and are preempted instantly when real pods need it. This converts the 40-240 second node provisioning step into zero.
3. **Cut the pod-side latency**: smaller images, pre-pulled on nodes, AppCDS or AOT to cut JVM start-up, and a startup probe tuned so readiness is not artificially delayed.
4. **Scale on a leading indicator** - queue depth, upstream request rate, or a scheduled scale-up for known patterns (KEDA cron scaler for a 09:00 spike). Predictive beats reactive whenever the pattern is predictable.
5. **Protect the existing capacity** while you wait: load shedding, rate limiting and a queue, so the service degrades gracefully rather than collapsing (`03-microservices` Q110-113).

The framing worth giving an interviewer: autoscaling is a **cost optimization**, not an availability mechanism. Availability during a spike comes from headroom and load shedding.

### Q115. VPA and KEDA

**VPA** adjusts a pod's CPU and memory *requests* based on observed usage. Three modes: `Off` (recommendations only), `Initial` (set at creation), and `Auto`/`Recreate` (evict and recreate the pod with new requests). In-place resizing landed as an alpha/beta feature but historically VPA had to restart the pod to change requests, which is its main cost.

**I use VPA in `Off` mode almost always** - as a recommender that tells me and the team what the right requests are, feeding a periodic right-sizing exercise (Q251, Q255). `Auto` mode is appropriate for batch workloads and for services where a restart is free, and inappropriate for anything where an unexpected eviction is a problem.

**KEDA** is an event-driven autoscaler: it provides scalers for dozens of external sources (Kafka consumer lag, SQS queue depth, RabbitMQ, Prometheus query, cron, database query) and translates them into an HPA under the hood. Two things it adds that the HPA cannot do alone: **scale-to-zero**, and a huge library of ready-made metric sources so you do not have to run and maintain the Prometheus Adapter plumbing yourself.

I reach for KEDA for **consumers and event-driven workloads** - it is the natural fit for "scale on queue depth" - and for anything wanting scale-to-zero. I use plain HPA with custom metrics for request-driven services where the metric is already in Prometheus.

**Conflicts with HPA:**

- **VPA and HPA must not both act on the same metric.** VPA changing CPU requests while the HPA scales on CPU utilization creates a feedback loop: VPA raises the request, measured utilization drops, HPA scales in, load per pod rises, VPA raises the request again. Rule: if HPA scales on CPU, VPA may only manage memory, and vice versa. Using a custom metric for HPA removes the conflict entirely, which is another argument for Q113.
- **KEDA creates and owns an HPA**, so you must not also define your own HPA for the same workload - two controllers writing `spec.replicas` fight.
- **Any of them versus a GitOps reconciler**: if `replicas` is set in git and Argo CD self-heals, it will fight the autoscaler. Omit `replicas` from the manifest or add it to `ignoreDifferences` (Q155).

### Q116. Zero-downtime cluster upgrades

**Control plane (EKS):** AWS upgrades it in place, one minor version at a time, with no downtime for the API server (it is HA behind an endpoint). Before you press the button:

1. Read the **version skew policy**: kubelet may be up to 3 minors behind the API server, so control plane first, nodes after - never the reverse.
2. Check the **deprecated API report** (`kubectl deprecations`, Pluto, or EKS's own insights) and fix anything using a removed API version. This is the most common upgrade break.
3. Check **add-on compatibility**: VPC CNI, CoreDNS, kube-proxy, CSI drivers, the mesh, cert-manager, the ingress controller. Upgrade the add-ons that need to lead, per the provider's matrix.
4. Upgrade a non-production cluster first, on the same manifests.

**Node groups:** the correct pattern is a **rolling replacement with surge**, never in-place patching.

1. Create new nodes with the new AMI/version (managed node group update does this, or a blue/green node group).
2. **Cordon** the old node (`kubectl cordon`) so nothing new schedules there.
3. **Drain** it (`kubectl drain --ignore-daemonsets --delete-emptydir-data`), which evicts pods **through the Eviction API**, so PodDisruptionBudgets are respected.
4. Wait for pods to be rescheduled and Ready elsewhere, then terminate the node.
5. Repeat, with a surge so total capacity never dips.

**PodDisruptionBudgets** are what make a drain safe: `minAvailable: 80%` or `maxUnavailable: 1` tells the eviction API to refuse evictions that would breach it, so the drain proceeds only as fast as replacement pods become Ready.

**What makes a drain hang** - the question inside the question:

- **A PDB that can never be satisfied**: `minAvailable: 1` with `replicas: 1`, or `minAvailable` equal to `replicas`. The eviction API refuses forever. This is the most common cause by far.
- **Pods that cannot be rescheduled** - no capacity, a node affinity that only matches the node being drained, or an RWO volume that cannot detach.
- **A StatefulSet whose replacement pod cannot start** (Q111).
- **Bare pods** with no controller - nothing recreates them, so `drain` refuses without `--force`.
- **A long `terminationGracePeriodSeconds`** multiplied across many pods.
- **A failing `preStop` hook** or a container ignoring `SIGTERM`, so every pod takes the full grace period.
- **`emptyDir` volumes**, which `drain` refuses to evict without `--delete-emptydir-data`.

The guardrail I put in place: a policy check that every Deployment with `replicas: 1` either has no PDB or has `maxUnavailable: 1`, and an alert on nodes that have been cordoned for more than an hour.

### Q117. Cluster topology for 60 services `[A]`

**One cluster per environment per region, not one per team and not one for everything.**

The reasoning is that clusters are the unit of *blast radius* and of *operational cost*, and those pull in opposite directions. A cluster per team gives beautiful isolation and a maintenance burden that scales linearly with team count - 15 clusters to upgrade every quarter, 15 sets of add-ons, 15 Prometheus stacks. One shared cluster minimizes that cost and means a bad upgrade or a control-plane incident takes down everything.

**The topology I would run:**

| Cluster | Purpose |
| --- | --- |
| `dev` | One cluster, namespace per team, generous quotas, no production data, aggressive cost controls and scale-to-zero overnight |
| `staging` | Production-shaped: same node types, same add-on versions, same policy set. This cluster exists to prove upgrades and manifests, so it must not diverge |
| `prod` (per region) | The production cluster. If multi-region, one per region, identical by construction |
| `prod-isolated` (only if justified) | A separate cluster for workloads with a genuinely different compliance or blast-radius requirement - PCI scope, a regulated tenant |

**Namespaces**: one per service, or per bounded context if services are small and co-owned. Namespace is the unit of RBAC, ResourceQuota, LimitRange, NetworkPolicy and cost attribution, so making it match the ownership boundary is what makes all of those usable. Team-level grouping goes in labels, not in the namespace name.

**Node pools:**

- A small **system pool** with a taint, for the control-plane-adjacent components (ingress, CoreDNS, Prometheus, the GitOps controller) - so a workload cannot starve the things you need during an incident.
- A **general pool**, autoscaled, taking the bulk of stateless services.
- **Specialized pools** where the workload genuinely differs: memory-optimized, ARM/Graviton, spot-only for interruption-tolerant work, and a stateful pool if needed.
- Taints on everything except the general pool, so scheduling there is deliberate.

**Blast radius controls within the cluster**, because the shared cluster is the risk I have accepted: ResourceQuota per namespace so one team cannot consume the cluster; PriorityClasses so system components and tier-1 services preempt batch; default-deny NetworkPolicy per namespace; PodDisruptionBudgets enforced by policy; topology spread across AZs for every Deployment; and separate node pools so a noisy workload's node-level effects are contained.

**What would change this**: a hard regulatory boundary (separate cluster, no argument); a tenant with a contractual isolation requirement; a workload whose Kubernetes version or CRD requirements conflict with everything else; or scale past a few thousand nodes where control plane limits force sharding.

*Hook: a cluster topology decision you made and what you would change with hindsight.*

---

## 8. Configuration and secrets management

### Q118. The twelve-factor config boundary

The principle: **config is everything that varies between deploys of the same artifact**; code is everything that does not. The test is "could this artifact be open-sourced without leaking credentials, and could it be deployed to a different environment without recompiling?"

**In config**: endpoints and connection strings, credentials, resource limits, replica counts, log levels, feature flag defaults, timeouts and pool sizes that differ by environment, and the observability endpoints.

**In the artifact**: business logic, the dependency set, the framework wiring, and - importantly - the *defaults* for everything above. A service should start with sensible defaults and require only the genuinely environment-specific values.

**Genuinely ambiguous cases**, which is what the question is actually about:

- **Timeouts, pool sizes and retry counts.** These vary by environment in practice, but they are also *behaviour* that should be tested. My rule: the default is in the artifact and tested; the environment may override, and any override is reviewed like code.
- **Feature flags.** A flag's *default* belongs in the artifact; its *current value* is runtime state in a flag service, which is neither config nor code (Q130).
- **Business rules that change often** - tax rates, thresholds, entitlements. These look like config, but they need versioning, review and audit, so they belong in data with a proper change process, not in an environment variable.
- **Anything with a schema.** A complex routing table or a rules document in a ConfigMap is configuration by location and code by nature. It needs validation and tests either way.

The twelve-factor rule that people over-apply is "config in environment variables". The useful part is *externalized and per-deploy*; the specific mechanism is Q120.

### Q119. ConfigMap versus Secret

**The actual difference is small and mostly conventional:**

- Secret values are **base64-encoded** in the object (which is encoding, not encryption, and provides no protection whatsoever).
- Secrets have a **type** (`Opaque`, `kubernetes.io/tls`, `kubernetes.io/dockerconfigjson`) that some controllers understand.
- Secrets are **not written to the node's disk in plaintext** - kubelet stores them in a `tmpfs` memory-backed volume.
- `kubectl describe` redacts Secret values but shows ConfigMap values.
- Both are capped at ~1 MiB.
- RBAC treats them as distinct resource types, which is the one genuinely important difference: you can grant `get configmaps` without granting `get secrets`.

**"Secrets are not encrypted" means, concretely:**

- **In etcd they are stored as plaintext by default.** Anyone with an etcd backup, a snapshot in S3, or filesystem access to an etcd node reads every secret in the cluster. This is the big one - see Q124.
- **Anyone with `get secrets` RBAC in the namespace reads them**, and a surprising number of default roles and operator service accounts have it.
- **Any pod in the namespace that can mount them** reads them, and by default a pod's ServiceAccount token grants API access.
- **Node compromise exposes every secret mounted by pods on that node**, and a node's kubelet can read any secret used by any pod scheduled to it.
- They appear in **`kubectl get secret -o yaml`**, in audit logs if request bodies are logged, and in `etcdctl` output.

The correct posture is: enable encryption at rest with a KMS provider, restrict `secrets` RBAC tightly, and prefer an external secret store (Q123) so the Kubernetes Secret is either absent or a short-lived cache rather than the system of record.

### Q120. Environment variables versus mounted files

| | Environment variables | Mounted files |
| --- | --- | --- |
| **Update behaviour** | **Fixed at container start.** Changing the ConfigMap does nothing until the pod restarts. | The kubelet **updates the file in place** (see Q121), so the application can reload without a restart. |
| **Leakage risk** | High. Visible in `/proc/<pid>/environ` to anything in the pod, inherited by every child process, printed by crash handlers and stack dumps, captured by `kubectl describe pod` for `env` (not `envFrom` secretRef values), and routinely logged by frameworks at start-up. | Lower. Readable only by processes that open the path, not inherited, not in process listings. Can be mode-restricted. |
| **Size and structure** | Flat strings; awkward for structured content; subject to environment size limits | Arbitrary size (to 1 MiB) and structure - YAML, JSON, PEM |
| **Application support** | Universal | Needs the application to read a path; Spring Boot handles it natively via `spring.config.import=configtree:/etc/config/` |
| **Subpath caveat** | n/a | A volume mounted with `subPath` is **not updated** - a very common gotcha |

**What I do**: non-sensitive configuration as environment variables where it is simple and the application expects them; **secrets as mounted files**, always, because of the leakage column. Spring Boot's `configtree` support means a secret mounted at `/etc/secrets/spring.datasource.password` binds automatically, so there is no application cost to doing this properly.

The strongest argument for files is the one that bites during an incident: an environment variable containing a password will eventually end up in a log line, an error report, or an APM trace, and you cannot un-log it.

### Q121. ConfigMap update not picked up `[T]`

Two entirely different mechanisms:

**Environment variables**: values are read once, when the container process is created, and copied into its environment. **There is no update path at all.** The ConfigMap can change a hundred times and the process will never see it. Only a pod restart (a new container) picks it up. This surprises people because the ConfigMap object visibly changed.

**Volume mounts**: kubelet watches the ConfigMap and updates the file. The mechanism is a symlink swap - kubelet writes the new content into a new timestamped directory under the volume, then atomically re-points the `..data` symlink, so readers never see a partial write. The **file content does change**, without a restart.

But there are three reasons it still looks like nothing happened:

1. **Propagation delay.** kubelet syncs on its `configMapAndSecretChangeDetectionStrategy` - by default a watch, but with a cache TTL (`--sync-frequency`, 1 minute default). The documented worst case is **the kubelet sync period plus the cache TTL, up to about 2 minutes**.
2. **`subPath` mounts are never updated.** If you mounted a single key with `subPath: application.yaml` to place it next to other files, kubelet cannot do the symlink swap, so the file is frozen at container start. This is the single most common cause.
3. **The application does not re-read the file.** The file changed; nothing told Spring Boot to reload it. You need `@RefreshScope` plus an actuator refresh, Spring Cloud Kubernetes' reload watcher, or a file-watching reload in the application. See Q122.

**How I avoid the whole class of problem**: annotate the pod template with a hash of the ConfigMap content (`checksum/config: {{ sha256 .Values.config }}` in Helm, or Kustomize's `configMapGenerator` with a name suffix hash). Any config change then changes the pod template, which triggers a normal rolling update. Configuration changes become deployments, with the same review, canary and rollback - which is what `03-microservices` Q185 is about.

### Q122. Hot reload versus rolling restart

**I default to a rolling restart**, implemented as the content-hash approach in Q121.

The reasoning: a rolling restart makes a configuration change **identical in every operational respect to a code change**. It is a versioned commit, it goes through the same review, it produces a deployment event, it rolls out progressively pod by pod, it is observable, and it is revertible by the same mechanism. Configuration changes cause a disproportionate share of outages precisely because they usually have none of those properties.

**What makes hot reload dangerous:**

- **It changes production without a deployment record.** There is no rollout, no canary, no revision history, and often no event correlated to the incident that starts four minutes later.
- **It is not atomic across pods.** Pods pick up the change at different times over a two-minute window, so the fleet is briefly running two configurations - which is fine for a log level and catastrophic for a routing rule or a schema toggle.
- **Partial application.** Many settings cannot actually be re-applied at runtime: a connection pool size, a thread pool, a listener port, anything bound at startup. `@RefreshScope` rebuilds beans, but only refresh-scoped ones, and the resulting object graph can be inconsistent (`02-spring` Q38).
- **No rollback path.** Rolling back a config change means another config change, applied with the same lack of ceremony.
- **It hides drift.** The running configuration is no longer what the last deployment says it is.

**Where hot reload is right**: log levels, feature flags (which have their own machinery for exactly this reason), and sampling rates - all things you want to change *during* an incident, where a restart would destroy the state you are trying to observe. Those are runtime controls, not configuration, and treating them as a separate category is the clean way to think about it.

### Q123. Secret storage options

| Approach | Where the secret lives at rest | In the pod | Notes |
| --- | --- | --- | --- |
| **Sealed Secrets** | **Encrypted in git**, decryptable only by the controller's private key in-cluster; plaintext in **etcd** after the controller unseals it | A normal Secret, env or file | Simple, GitOps-native. But the plaintext is a normal Secret in etcd, rotation means re-sealing and committing, and losing the controller key loses everything. |
| **External Secrets Operator** | In the **external store** (Secrets Manager, Vault, Parameter Store). ESO **syncs a copy into a Kubernetes Secret**, so plaintext is in **etcd** | A normal Secret | Best ergonomics: applications need no changes, rotation propagates on a refresh interval. The copy in etcd is the compromise. |
| **CSI Secrets Store driver** | In the external store only. **Never written to etcd** | Mounted as a **tmpfs file**, fetched at pod start via the pod's workload identity | The strongest option for at-rest posture. Costs: file-only (no env vars, unless you enable the optional Secret sync which reintroduces etcd), and the pod cannot start if the store is unreachable. |
| **Vault Agent Injector** | In Vault only | A **sidecar/init container** writes rendered files into a shared memory volume and re-renders on rotation | Never in etcd, supports dynamic short-lived secrets and lease renewal natively. Costs: an extra container per pod, a hard runtime dependency on Vault, and templating complexity. |

**My default** is **External Secrets Operator** for most estates - it is the best trade between security posture and the fact that every tool in the ecosystem understands a Kubernetes Secret - moving to the **CSI driver or Vault injector** for the highest-sensitivity workloads, where keeping plaintext out of etcd is worth the operational cost. Sealed Secrets is a reasonable starting point for a small estate with no external store, and a thing to migrate off later.

### Q124. Encryption at rest in etcd

By default, **etcd stores Secret values as plaintext**. The `EncryptionConfiguration` on the API server changes that with a list of providers per resource type.

**Envelope encryption with a KMS provider** works like this: the API server generates a **data encryption key (DEK)** per secret (or per set, depending on the KMS version), encrypts the secret with it locally using AES-GCM, then calls KMS to encrypt the DEK with a **key encryption key (KEK)** that never leaves KMS. What is written to etcd is the ciphertext plus the wrapped DEK. On read, the API server asks KMS to unwrap the DEK, then decrypts locally.

Why envelope rather than calling KMS directly: only the small DEK crosses the network, KMS is not in the path for every byte, DEKs can be cached, and rotating the KEK does not require rewriting the data (though re-encrypting is still needed for the old KEK to be truly retired). KMS v2 (stable in 1.29) adds per-resource DEK caching and key ID tracking, which fixed the performance and rotation problems of v1.

**Alternatives to KMS**: `aescbc` and `secretbox` providers use a key held in a file on the control plane nodes - better than nothing, but the key sits next to the data, so it does not protect against host or backup compromise. On EKS, KMS encryption of secrets is a one-checkbox setting and there is no reason not to enable it.

**What an etcd backup contains without encryption**: every object in the cluster in plaintext, including **every Secret value** - database passwords, API keys, TLS private keys, ServiceAccount tokens, registry credentials. An etcd snapshot in an S3 bucket with loose permissions is a complete compromise of every credential the cluster holds, and it is a startlingly common finding. It also means secret rotation is retroactively defeated: an old backup still contains the old credentials, which may still be valid.

The important corollary: enabling encryption does **not** encrypt existing secrets. You must force a rewrite (`kubectl get secrets -A -o json | kubectl replace -f -`) after enabling it.

### Q125. Rotating a database credential with no downtime

The core requirement is that **two credentials must be valid simultaneously**, because pods pick up the new one at different times. Any rotation design that assumes an instant cutover will drop connections.

The sequence:

1. **Create a second credential** in the database - a new password on a second user, or a second password on the same user if the engine supports it (MySQL 8 dual passwords, Oracle gradual password rollover). Do **not** change the existing one.
2. **Write the new credential to the secret store** as the current version. Both old and new are now valid at the database.
3. **Propagate.** With ESO, the sync interval writes it to the Kubernetes Secret; with the CSI driver or Vault agent, it lands on the next fetch or re-render.
4. **Roll the pods.** Even with a file mount and hot reload, I prefer a rolling restart here, because a connection pool holds credentials at connection creation and reload semantics vary by driver. Twelve pods roll over a few minutes, each taking the new credential; the old credential covers everything not yet rolled.
5. **Verify** that no connections are using the old credential - most engines expose the authenticating user or you can use a distinct username per version and check `pg_stat_activity` / `performance_schema`.
6. **Only then, revoke the old credential.** This is the step people do too early.

**The better answer** is to remove the choreography entirely with **dynamic secrets**: Vault's database secrets engine issues a unique, short-lived credential per pod at start-up and revokes it on lease expiry. Rotation stops being an event - every pod restart is a rotation, and the maximum exposure of any credential is its TTL. That is Q127.

### Q126. Secret committed six months ago `[T]`

**Assume it is compromised.** Public repositories are scraped continuously - credentials committed to GitHub are typically exploited within minutes - and even for a private repository, six months means an unknown number of clones, forks, CI caches and developer laptops hold it.

In order:

1. **Rotate or revoke the credential first.** Before any investigation, before rewriting history, before telling anyone. Revocation is the only action that actually reduces risk, and everything else can be done afterwards. If revocation is disruptive, issue a new credential, cut over, then revoke.
2. **Determine the blast radius.** What did that credential grant, to what, and from where? Was it scoped or broad? This drives everything that follows.
3. **Hunt for use.** Search the audit logs - CloudTrail, the database's authentication log, the API provider's access log - for use of that credential from unexpected sources or at unexpected times, over the whole six-month window. This is the step that determines whether it is a hygiene issue or an incident.
4. **Declare an incident if there is any evidence of misuse**, and follow the incident process rather than handling it quietly.
5. **Purge the history**, knowing it is cleanup and not remediation. `git filter-repo` or BFG, force-push, and then ask the platform to expunge cached views - GitHub keeps unreachable commits accessible by SHA until garbage-collected, and forks retain them. This is why step 1 is first.
6. **Notify** per policy - security team, and the credential's owner if it is a third party's.
7. **Fix the systemic cause**: push protection and pre-commit secret scanning so it cannot happen again, plus a historical scan of every repository, because if it happened once it has happened elsewhere.

The judgement being assessed is whether you rotate first or investigate first. Rotate first.

*Hook: a leaked credential you handled, and how long revocation actually took.*

### Q127. Dynamic secrets versus static rotated secrets

A **static rotated secret** is a long-lived credential that is periodically replaced. Between rotations it is shared by every consumer, exists in several places, and is valid for weeks or months.

A **dynamic secret** is generated per consumer, on demand, with a lease. Vault's database engine creates an actual database user with a TTL when a pod requests one, and revokes it when the lease expires or is explicitly returned.

**What it changes about blast radius:**

- **Exposure window becomes the TTL.** A leaked credential is useful for an hour, not until the next quarterly rotation. This converts "we must rotate everything and audit six months" (Q126) into "it expired before we finished reading the alert".
- **Attribution becomes possible.** Each consumer has its own credential, so the database's authentication log identifies *which pod* did something. With a shared credential, every audit trail says "the application".
- **Revocation becomes granular.** You can revoke one workload's access without a coordinated rotation across the estate.
- **Rotation stops being an event.** No choreography, no coordination, no "who still holds the old one" - which removes an entire class of operational risk and the outages that come with it.
- **Least privilege becomes practical**, because generating a credential with exactly the needed grants is cheap.

**What it costs**: Vault becomes a hard runtime dependency on the start-up path of every service - if Vault is down, no pod can start, so it needs to be as available as the database itself. It adds lease renewal logic (the agent handles it, but connection pools must cope with a credential expiring mid-life). Each pod creating a database user adds load and object churn to the database, which matters at high pod counts. And it is significant operational investment.

**The pragmatic position**: dynamic secrets for databases and cloud credentials where the value is highest; workload identity (Q128) wherever the platform supports it, because that is dynamic secrets with none of the operational cost; and static rotated secrets for third-party API keys where nothing better exists.

### Q128. IRSA and the token exchange

IAM Roles for Service Accounts lets a pod obtain AWS credentials with **no stored key anywhere**, using OIDC federation.

The setup: the EKS cluster exposes an **OIDC discovery endpoint** (`/.well-known/openid-configuration` and a JWKS) with the public keys the API server uses to sign ServiceAccount tokens. That endpoint is registered in IAM as an **OIDC identity provider**. An IAM role's trust policy then says "allow `sts:AssumeRoleWithWebIdentity` for tokens from this provider whose `sub` claim is `system:serviceaccount:<namespace>:<serviceaccount>`".

The exchange, step by step:

1. A ServiceAccount is annotated `eks.amazonaws.com/role-arn: arn:aws:iam::123:role/my-role`.
2. A pod uses that ServiceAccount. An **admission webhook** (the pod identity webhook) mutates the pod, adding a **projected service account token volume** with `audience: sts.amazonaws.com` and a short expiry, plus the environment variables `AWS_ROLE_ARN` and `AWS_WEB_IDENTITY_TOKEN_FILE`.
3. The **kubelet requests the token from the API server**, which signs a JWT with claims identifying the namespace, ServiceAccount, pod name and UID, audience `sts.amazonaws.com`, and a short lifetime (1 hour by default). kubelet writes it to the volume and **rotates it automatically** at ~80 percent of its lifetime.
4. The AWS SDK in the application sees those environment variables and, via the `WebIdentityTokenFileCredentialsProvider`, calls **`sts:AssumeRoleWithWebIdentity`** with the token.
5. **STS validates the token**: it fetches the cluster's JWKS from the OIDC endpoint, verifies the signature, checks the audience and expiry, then checks the role's trust policy against the `sub` claim.
6. STS returns **temporary credentials** (access key, secret, session token) valid for up to an hour. The SDK caches and refreshes them.

Nothing long-lived is ever stored, the credential is scoped to one ServiceAccount in one namespace in one cluster, and revocation is a trust policy edit. **EKS Pod Identity** (newer) does the same thing with a node-local agent and a simpler association API, removing the need to manage an OIDC provider per cluster - worth naming as the current direction.

The security caveat: the boundary is the **ServiceAccount**, so any pod that can use that ServiceAccount gets the role, and anyone who can create a pod in that namespace can use it. Namespace-level RBAC is therefore part of your IAM boundary.

### Q129. Configuration drift between environments

**Detection:**

- **Compare the rendered manifests, not the templates.** Render every environment's Helm or Kustomize output and diff them field by field, ignoring the fields that are *supposed* to differ (replica counts, resource sizes, endpoint hostnames). Anything else is drift, and this catches the case where staging quietly got a flag production never received.
- **Detect drift from git**, which GitOps gives you for free: Argo CD reporting `OutOfSync` *is* drift detection, and a resource that has been out of sync for a week is a human change nobody recorded (Q154).
- **Expose the effective configuration at runtime** and compare it. A `/actuator/configprops` snapshot per environment, collected on deploy, is a direct answer to "why does it behave differently there".
- **Alert on the difference set changing**, not on the difference existing. Every environment differs; what matters is a *new* difference nobody intended.

**The structure that prevents "it works in staging" as a class:**

1. **One base, thin overlays.** A single set of manifests with per-environment overlays that contain *only* values that must differ, and a hard review rule that adding a key to an overlay requires justification. The moment overlays contain logic, drift is inevitable.
2. **The same artifact digest promoted through environments** (Q9), so the code is provably identical.
3. **Environment differences are declared and enumerable.** A list of "these 11 values differ by environment, and nothing else may" is testable - lint the overlays against it.
4. **Every environment is created by the same automation.** If staging was built by Terraform and production by hand two years ago, no manifest discipline will save you.
5. **Production-shaped staging** on the dimensions that matter for correctness: same Kubernetes version, same add-on versions, same policy set, same TLS posture, same network policy. Scale can differ; behaviour must not.
6. **Periodically rebuild a lower environment from scratch.** It is the only way to find the drift that accumulated as manual fixes, and it validates the disaster-recovery path at the same time.

### Q130. Feature flags as configuration

**Where the state lives**: in a flag service - LaunchDarkly, Unleash, Flagsmith, or an in-house service - which is the system of record. Applications embed an SDK that maintains a **local, in-memory copy** of the ruleset, updated by streaming or polling. Evaluation is always **local and synchronous**: the SDK evaluates the rules against the supplied context in microseconds, with no network call in the request path. That is the architectural point - a flag check must never be a remote call.

**The failure mode when the flag service is unreachable:**

- **Already-running pods are unaffected**, because they evaluate from the local cache. They keep serving with the last-known ruleset, potentially for hours. This is the desired behaviour and it means a flag service outage is usually invisible.
- **The dangerous case is a cold start.** A pod that starts during the outage has no cached ruleset. Whatever it does then is your real availability posture, and it is determined by two things: whether the SDK is initialized *blocking* (start-up hangs or times out) or *non-blocking* (the service starts and every flag returns its code default), and whether you persisted the last-known ruleset to disk or to a ConfigMap.
- **The compounding case**: a scale-out event during a flag service outage means every new pod is on defaults while the existing pods are on the real ruleset - so the fleet is inconsistent, which is far worse than being uniformly wrong.

**My defaults:**

1. **Every flag call site supplies a code default**, and the default is the **safe** value - usually "the old behaviour". A flag whose default enables a new code path is a landmine.
2. **Non-blocking initialization with a bounded wait.** The service starts even if the flag service is unreachable; readiness may wait a few seconds, but never indefinitely.
3. **Persist the last-known-good ruleset** - a file or a ConfigMap the SDK falls back to - so a cold start during an outage gets the real values rather than defaults.
4. **Treat the flag service as a tier-1 dependency** with its own SLO, and monitor SDK staleness (time since last successful ruleset update) as a metric with an alert.
5. **A kill-switch path that does not depend on it** for the flags that matter most during an incident.

### Q131. Config and secrets strategy for EKS plus a legacy VM fleet `[A]`

**The design goal is one system of record with two delivery mechanisms**, not two parallel systems. The failure mode I am designing against is a credential that exists in Vault for the EKS services and in a Chef data bag for the VMs, rotated on different schedules by different teams.

**System of record:**

- **Non-secret configuration** lives in git, per environment, alongside the manifests. It is reviewed, versioned and promoted like code.
- **Secrets** live in one external store. I would pick **AWS Secrets Manager plus Parameter Store** if the estate is AWS-only and the requirements are ordinary, or **Vault** if we need dynamic secrets, cross-cloud reach, or a PKI. One store, one naming convention (`/<env>/<service>/<key>`), one rotation policy, one audit log.

**Delivery to EKS:**

- Configuration via ConfigMaps generated by Kustomize with a content hash, so a config change is a rolling deployment (Q121-122).
- Secrets via **External Secrets Operator** syncing from the store, mounted as **files** not environment variables (Q120), with the CSI driver for the highest-sensitivity workloads.
- **Workload identity (IRSA / Pod Identity)** for every AWS API call, so no AWS keys exist as secrets at all. This removes the largest single category of stored credentials.

**Delivery to the VM fleet:**

- The same store, accessed with **instance-profile identity** - the VM equivalent of workload identity - so again no bootstrap key.
- A small agent on each host (Vault Agent, or a systemd unit calling the AWS SDK) renders configuration and secrets to files with restricted permissions, and re-renders on rotation. Same file paths and same naming convention as the EKS side, so the application code is identical.
- Configuration is delivered by the existing configuration-management tool, but **sourced from the same git repository** as the Kubernetes overlays - rendered differently, defined once.

**Cross-cutting:**

- **No secret in git, ever**, on either side - enforced by push protection and pre-commit scanning.
- **Rotation is designed for two-valid-credentials** (Q125) because the VM fleet will always propagate more slowly than the cluster.
- **Audit**: every secret read is logged with the identity, on both sides, into the same place.
- **A migration ratchet**: every service moved off the VM fleet also moves to the new pattern, and no new secret is ever created in the legacy mechanism. The legacy path is frozen and drains rather than being migrated as a project.

**The honest trade-off**: this costs more than letting each platform use its native mechanism, and the benefit is invisible until the day you have to rotate a credential used by both, or answer an auditor's question about who read what. Both of those days come.

*Hook: a secrets migration you ran across two platforms, and the credential that turned out to be used by something nobody knew about.*

---

## 9. Deployment and release strategies

### Q132. Recreate, rolling, blue/green and canary

| | Capacity needed | Rollback speed | Risk exposure |
| --- | --- | --- | --- |
| **Recreate** | 1× | A full redeploy of the old version - minutes | Total: 100 percent of traffic hits the new version, after an outage window |
| **Rolling** | 1× to 1.25× | A reverse rolling update - minutes, and it gets slower as the rollout progresses | Gradual but uncontrolled: an increasing share of traffic, with no gate between steps |
| **Blue/green** | **2×** | A traffic switch back - **seconds** | Binary: 0 percent then 100 percent. The new version is verified before any user traffic, but the cutover is all-at-once |
| **Canary** | 1× to 1.25× | Shift weight back - **seconds** | Lowest and *controlled*: an explicitly chosen percentage, with automated analysis gating each increase |

The distinctions that matter beyond the table:

- **Rolling is the only one of these that Kubernetes does natively**, and it is also the only one with no verification gate - which is Q86.
- **Blue/green's expensive property is capacity; its valuable property is that rollback is a routing change**, not a deployment. That is the difference between a 20-second recovery and a five-minute one.
- **Canary's value is not the small percentage; it is the automated comparison.** A canary nobody analyzes is just a slow rolling update.
- All four say nothing about **data**. Every one of them is constrained by whether the old and new versions can share a schema and a message format (Q142, Q144), and that constraint is usually the binding one.

### Q133. Separating deploy from release

**Deploy** is putting the code on the infrastructure. **Release** is making the behaviour visible to users. They are separated by a runtime switch - a feature flag, a routing weight, or an entitlement check.

**Mechanically**, this means: merge and deploy code whose new paths are behind a flag defaulted off; the artifact reaches production and runs, exercised only by internal traffic or by nobody; then release is a flag change, possibly progressive by cohort, entirely independent of the deployment.

**What it changes about a Friday deploy:**

- The deploy carries only the risk of the *unconditional* code - the plumbing, the dependency updates, the refactoring. The risky behaviour is not active.
- Rollback of the release is a flag flip: **seconds, no build, no pipeline, no rollout**, and available to whoever is on call rather than requiring a deployer.
- The blast radius of a release is controllable and reversible independently of the deployment, so you can release to 1 percent on a Friday afternoon in a way you could never deploy.
- Deployment frequency can rise without release risk rising, which decouples the two things a release freeze was trying to control.

The honest caveat: it moves risk rather than eliminating it. Flags have their own failure modes (Q141), the unconditional code is still deployed, and a flag that changes behaviour in a stateful path is not reversible just because the flag is. "Friday deploys are fine" is a conclusion you earn by having the rollback and the observability, not by having flags.

### Q134. Blue/green on Kubernetes

**Implementation**: two complete Deployments, `app-blue` and `app-green`, differing by a version label. A single Service selects on that label. Cutover is a change to the Service's `selector` - or, with an ingress or mesh, a change to which backend receives 100 percent of the weight.

```yaml
kind: Service
spec:
  selector:
    app: orders
    version: green     # change this to cut over
```

The Service-selector version is the simplest and is atomic from the API's point of view, but propagation is still subject to the endpoint chain of Q103. The ingress or mesh weight version gives you finer control and is what Argo Rollouts uses.

**In-flight requests.** The old pods keep running - that is the point of blue/green - so requests already in flight complete against blue. New connections go to green. With HTTP keep-alive, clients hold connections to blue and will keep using them until the connection is closed, so the cutover is not instantaneous at the connection level. You either wait out the connection lifetime before scaling blue down, or force a drain by failing blue's readiness. Either way, **do not scale blue down immediately** - keeping it running is what makes rollback fast, so it should stay up for at least the agreed rollback window.

**Database state** is the hard part and the reason blue/green is often not really available. Both versions share one database, so the schema must satisfy both simultaneously - expand-contract (Q142), no destructive DDL in the deploying release, and no migration that only the new version can tolerate. If green migrates the schema on start-up and blue cannot read it, you have blue/green with no rollback, which is the worst of both.

**Caches** need thought: a shared Redis with a changed serialization format corrupts blue's view, so version your cache keys or namespace them per version. In-process caches are fine because the pods are separate, but they mean green starts cold and its first minutes of latency are not representative.

### Q135. Cutover succeeded, rollback failed `[T]`

Rollback is not the reverse of the cutover because the cutover had **side effects that the routing change does not undo**.

1. **The schema moved.** Green ran a migration - added a NOT NULL column, dropped an old one, changed a type. Blue's code cannot read the new schema, so routing back sends traffic to an application that now throws on every query. The routing reverted; the database did not.
2. **Data was written in the new format.** Green wrote rows, cache entries, or messages that blue cannot deserialize - a new enum value, a new JSON shape, a changed serialization version. Blue comes back and immediately fails on green's data. This is the most common one and it is invisible until rollback.
3. **Blue is no longer capable of serving.** It was scaled to zero to save capacity; its pods were evicted; its image was garbage-collected from the nodes; its ConfigMap was updated in place by the deploy; or its dependencies moved on - a downstream service was deployed in the same window and no longer speaks blue's contract. Blue existed as an object, not as a running system, and nobody tested that assumption.
4. **External state changed.** Green published events, called a partner API, triggered a workflow, or advanced a Kafka consumer group offset. Consumers have processed green's events; the routing change cannot recall them.

The design conclusions: keep blue **running and receiving health checks** for the whole rollback window; make every schema and format change backward compatible for at least one release (expand-contract); version your serialized formats and your cache keys; and **test the rollback**, in staging, as part of the release - a rollback path that has never been executed is a hypothesis.

*Hook: a rollback that failed and what made it impossible.*

### Q136. Canary analysis

**Signals to compare**, in priority order:

1. **Error rate** - HTTP 5xx and application-level errors, as a *ratio* not a count, because the canary serves less traffic.
2. **Latency** - p95 and p99, compared as a ratio to baseline. Not the mean.
3. **Business or domain signals** - orders placed, payments succeeded, messages processed per unit of traffic. These catch the failures that are not errors, which are the expensive ones.
4. **Resource signals** - CPU, memory growth, restart count, GC pause time. These catch leaks and regressions that will surface later.
5. **Downstream effects** - error rate and latency at the services the canary calls.

**What to compare against**: the **baseline**, meaning a control group running the old version *at the same time*, not the historical values of the same metric. Comparing the canary against yesterday conflates the code change with time-of-day, traffic mix and downstream conditions. Argo Rollouts and Flagger both support running an explicit baseline Deployment alongside for exactly this reason.

**Over what window**: long enough for the metric to be statistically meaningful, which is a function of traffic volume and the size of the effect you want to detect, not of the clock. The arithmetic: to detect a rise in error rate from 0.1 percent to 0.5 percent with reasonable confidence you need on the order of a few thousand requests in the canary. At 5 percent of 100 requests per second, that is a few minutes; at 5 percent of 2 requests per second, it is hours - and in that case a canary by traffic percentage is the wrong tool.

**Avoiding a meaningless sample:**

- **Set a minimum request count per step**, not just a duration. Promote on evidence, not on a timer.
- **Use ratio metrics and confidence intervals**, not raw thresholds. A single 500 in 40 requests is 2.5 percent error rate and means nothing.
- **Weight by traffic**: start at a percentage that yields enough volume, and increase step size as confidence grows.
- **Fail open on no data.** If the analysis query returns nothing, that is a failure of the analysis, not a pass. Treat "no data" as inconclusive and halt, never as success - this is a real and common misconfiguration.
- **Account for multiple comparisons**: checking twelve metrics at 95 percent confidence gives you a false alarm most of the time. Either use fewer, better metrics, or correct for it.

### Q137. Argo Rollouts and Flagger

Both replace the Deployment's rollout logic with a controller that gates each step on analysis.

**Argo Rollouts** introduces a `Rollout` CRD in place of a Deployment. Its state machine:

1. A spec change creates a new **ReplicaSet** (the canary) and scales it to the weight of the current step.
2. Traffic routing is updated to send the step's percentage to the canary.
3. If the step has analysis, an **AnalysisRun** is created, which executes `metrics` queries (Prometheus, Datadog, CloudWatch, a job, a web request) at an interval, evaluating `successCondition` / `failureCondition` expressions.
4. On success and after the step's duration, it advances to the next step. On failure - or on `failureLimit` consecutive failures - it **aborts**: traffic is shifted back to the stable ReplicaSet and the canary is scaled down.
5. A `pause` step with no duration waits for a manual `promote`, which is how you insert a human gate.
6. When the last step completes, the canary ReplicaSet becomes stable and the old one is scaled down.

States are `Progressing`, `Paused`, `Degraded`, `Healthy`, plus `Aborted`. Analysis can also run as a **background** AnalysisRun for the whole rollout, and as pre- and post-promotion hooks.

**Flagger** takes the opposite approach: it leaves your Deployment alone and generates a shadow "primary" Deployment plus the routing objects, driving a metric-checked weight progression via a `Canary` CRD. Functionally similar; the difference is that Flagger keeps the Deployment as the source of truth (nicer for GitOps and for tooling that expects Deployments) while Argo Rollouts replaces it (more control, tighter Argo CD integration).

**Interaction with the mesh or ingress**: the controller does not move traffic itself. It writes to whatever routing object the provider supports - an Istio `VirtualService`'s weighted destinations, an SMI `TrafficSplit`, an NGINX ingress canary annotation, an ALB target group weight, a Gateway API `HTTPRoute` `backendRefs` weight. Two Services (stable and canary) select the two ReplicaSets, and the controller adjusts the weights between them. Without a traffic provider, both controllers fall back to **replica-count-based** approximation, where "20 percent" means "20 percent of the pods" and the actual traffic split is whatever the Service's random selection produces - much coarser, and not usable for small percentages.

### Q138. Canary passes at 5 percent, fails at 100 `[T]`

1. **The canary was not representative of traffic.** Routing at 5 percent by connection or by random selection does not sample uniformly across tenants, endpoints or payload shapes. A bug on a code path used by one large customer, a monthly batch, or an admin endpoint simply was not exercised. Sticky sessions and long-lived HTTP/2 connections make this worse - a "5 percent" canary can receive traffic from a handful of clients.
2. **Load-dependent failure.** At 5 percent the pod handles a twentieth of the load. A connection pool that is too small, a lock contention point, a memory footprint that only manifests at concurrency, a GC configuration that is fine at low allocation rate - none of these appear until full traffic. Resource limits that are adequate at 5 percent are the classic version.
3. **Capacity and downstream effects.** At 100 percent the new version's higher per-request cost - an extra query, a larger payload, a new downstream call - saturates a shared dependency: the database's connection limit, a third-party rate limit, a cache that now misses. The canary was subsidized by the 95 percent of traffic still on the old version, and the dependency's capacity only broke when everything moved.
4. **Time-dependent failure.** A slow leak, a certificate, a scheduled task, a cache that was warm on the canary because the old pods populated it, or state that accumulates. Five minutes at 5 percent cannot observe a failure with an hour-long fuse.
5. **The old version was masking it.** Anything with shared state - a queue consumed by both versions, a cache written by both, a leader election - can behave correctly while a majority of old instances is present and fail when they are gone. Quorum and consumer-group rebalancing are the specific cases.

**What reduces it**: run the canary longer and at higher weight before full promotion; include resource and downstream metrics in the analysis, not just error rate; deliberately route a representative slice (by header or cohort, Q139) rather than a random percentage; shadow production traffic to the new version at full volume before the canary; and keep the rollout progressive right through to 100 percent rather than jumping from 20 to 100 in one step.

### Q139. Progressive delivery by cohort

Instead of "5 percent of requests", route "all requests from these users" - internal staff, then beta customers, then one region, then a percentage of the rest.

**When it is correct:**

- **Low traffic volume**, where a percentage split never accumulates a statistically meaningful sample (Q136). A cohort gives you concentrated signal.
- **Stateful or session-bound behaviour**, where a user bouncing between versions on successive requests is incoherent - a multi-step workflow, a shopping cart, anything with client-side state that must match the server.
- **When the risk is per-tenant** rather than per-request: a B2B product where one customer's breakage is the whole incident, so you want to control *which* customers are exposed.
- **When you want human feedback**, not just metrics - dogfooding to internal users first is a cohort rollout and it catches the failures metrics never see.
- **Regulatory or contractual constraints** on which populations can receive a change.

**What it requires of the router:** the ability to make a **deterministic, consistent routing decision from request attributes** - a header, a cookie, a JWT claim, a hashed user ID - rather than a random weight. Concretely: header-based matching in an Istio `VirtualService` or a Gateway API `HTTPRoute`, or the same logic in the gateway. It also requires that the attribute is **present and trustworthy at the routing layer**, which usually means the edge must have already authenticated the request - so the identity has to be extracted before routing, and that pushes cohort logic to the gateway rather than the mesh.

The honest limitation: cohorts give you *consistency* but a *biased* sample. Internal users are not real users, and beta customers are self-selected. So cohorts are usually a first stage, followed by a percentage-based canary once the obvious problems are out.

### Q140. Feature flag taxonomy and lifecycle

| Type | Purpose | Lifetime | Policy |
| --- | --- | --- | --- |
| **Release flag** | Hide incomplete work; decouple deploy from release | **Days to weeks** | Must have an owner and an expiry date at creation. Removed as part of the feature's definition of done. A release flag past its expiry fails a build check. |
| **Operational / kill switch** | Turn off a subsystem, shed load, disable an expensive path during an incident | **Permanent, deliberately** | Owned by the service team, documented in the runbook, and **tested** - an untested kill switch does not work. Reviewed annually for whether it is still needed. |
| **Experiment / A-B flag** | Measure a hypothesis | **The experiment's duration** | Owned by the experiment, expires with it. The result must be actioned - the winning variant becomes the code, and the flag goes. |
| **Permission / entitlement flag** | Control access by plan, tenant or licence | **Permanent, but it is not a flag** | This is product configuration and belongs in the entitlement system with proper data modelling, not in the flag service. Putting it there is how flag counts reach 340. |

The lifecycle discipline that actually works: **every flag has an owner, a type and an expiry at creation** (enforced by the flag service's API, not by convention), a **dashboard of flags past expiry** that is reviewed in the team's regular cadence, and **flag removal is part of the story**, not a follow-up ticket. The single most effective control is making it *impossible to create a flag without an expiry date*.

### Q141. 340 flags and nobody knows `[T]`

**How it happened** - four mechanisms, all of them organizational:

1. **No expiry at creation.** A flag is created in thirty seconds and removing it requires understanding the code, testing both paths and shipping a change. The asymmetry guarantees accumulation.
2. **No taxonomy.** Permission flags, experiment flags and release flags are all "flags", so there is no rule that distinguishes "should have been deleted in March" from "must never be deleted".
3. **Removal is nobody's story.** The feature shipped, the team moved on, and cleanup is invisible work that competes with visible work. It always loses.
4. **Fear.** After enough time, nobody knows what the flag guards, so removing it is a risk with no reward. That fear is rational, which is why this compounds rather than self-corrects.

**Digging out**, in order:

1. **Instrument evaluation.** Every flag evaluation reports flag name, variation returned, and whether it matched a targeting rule. Within a week you have data. This is the step that converts fear into fact.
2. **Classify by that data.** Flags never evaluated → the code path is dead; remove the flag *and* the dead branch. Flags always returning the same value for everyone → the decision is made; remove the flag and inline the winning branch. Flags with real targeting variation → these are the small set that matter, and they get individually reviewed.
3. **Batch the trivial ones.** The first two categories are usually 70-80 percent of 340, and they can be removed in bulk with mechanical PRs, one service at a time, with the normal canary.
4. **Assign the rest an owner and an expiry.** Anything unowned after a deadline is removed by default, announced in advance.
5. **Then fix the mechanism**: mandatory owner and expiry at creation, an expired-flag report, a lint rule that fails a build with a flag past expiry, and a rule that permission flags live in the entitlement system instead.

The change that prevents recurrence is making **flag debt visible on the same dashboard as other health metrics**, because unmeasured debt is unbounded debt.

*Hook: a flag cleanup you drove and what the evaluation data revealed.*

### Q142. Zero-downtime migrations and expand-contract

During a rolling deploy, **old and new code run simultaneously against one schema**. So the schema must be compatible with both, which means no change can be both structural and immediate.

**Expand-contract**, for renaming `customer_name` to `full_name`:

| Phase | Deploy | Schema | Both versions can run? |
| --- | --- | --- | --- |
| **1. Expand** | none | `ADD COLUMN full_name` (nullable, no default that rewrites the table) | Yes - old code ignores it |
| **2. Dual write** | Code writes both columns, reads `customer_name` | none | Yes |
| **3. Backfill** | none | Batched `UPDATE` copying old → new, throttled | Yes |
| **4. Switch reads** | Code reads `full_name`, still writes both | none | Yes |
| **5. Stop writing old** | Code writes only `full_name` | none | Yes - but rollback past here is now unsafe |
| **6. Contract** | none | `DROP COLUMN customer_name` | Only new code |

Each phase is a separate deployment, and each is independently revertible **except across the boundary at phase 5-6**. That boundary is the point of no return, and it should be crossed days or weeks later, deliberately, once you are certain no rollback is wanted.

**What makes a migration non-rollbackable:**

- **Any destructive change**: `DROP COLUMN`, `DROP TABLE`, dropping an index the old plan needs, narrowing a type, adding a `NOT NULL` constraint the old code violates.
- **Lossy transformations**: splitting a column into two and discarding the original, changing units, re-encoding data. The information to reverse it is gone.
- **Data written in a format only the new version understands.** Even with a purely additive schema, if new code writes a value old code cannot parse, you cannot roll back the *code* (Q135).
- **Anything that has already left the system** - events published, external calls made.

The lock-level detail of which DDL is safe in which engine is `06-database` Category 14; the point here is the **deployment sequencing** around it.

### Q143. Rolled back the app, the migration had run `[T]`

**My position: migrations are not rolled back. They are rolled forward.**

The reasoning is that a down-migration is code that has almost never been executed, written at the time of the up-migration by someone who was not thinking about the failure case, against a database whose state at rollback time is not the state it was written for. Running an untested destructive script against production during an incident is a worse risk than the one you are trying to escape. And in the common case the down-migration is *impossible* anyway - the data it would need to restore no longer exists.

**What that implies for how migrations are written:**

1. **Every migration must be backward compatible with the previous release.** This is the load-bearing rule. If the schema after migration N works with application version N-1, then rolling back the application is safe and the migration simply stays.
2. **Therefore: no destructive DDL in the same release as the code that stops using it.** Expand and contract are separate releases, separated by time (Q142).
3. **Migrations are additive by default**, and anything destructive requires an explicit review and a deliberate decision that the rollback window has passed.
4. **Migrations run separately from the application**, as a pipeline step, not on application start-up - so a rollback of the deployment does not re-trigger or re-order anything, and so N pods do not race to migrate.
5. **A migration must be idempotent and re-runnable**, because it will be retried.
6. **If you truly cannot avoid a breaking change**, the recovery path is a *forward* fix plus, in the worst case, a point-in-time restore - and that path is documented and rehearsed before the migration ships, not improvised.

Stated crisply for an interview: **the rollback plan for a migration is that it does not need to be rolled back**, and that is a property you design in, not a decision you make at 3 am.

### Q144. Contract compatibility during a rolling deploy

The requirement: during the rollout, both versions of the producer and both versions of the consumer coexist, in every combination. So a change must be safe in all four pairings.

**For an API, what must be true:**

- **New request fields are optional** with a safe default, so old clients that omit them work.
- **New response fields are additive**, and consumers ignore unknown fields (Jackson's `FAIL_ON_UNKNOWN_PROPERTIES=false`, which is Boot's default - verify it).
- **No field is removed, renamed or retyped** in one release. Removal is expand-contract: add the new, migrate consumers, then remove.
- **No enum value is added to a response** unless consumers are known to tolerate unknown values - this is a very common break, because a strict deserializer throws on an unrecognized enum.
- **Semantics do not change silently.** Changing the meaning or unit of an existing field is a breaking change with a non-breaking signature, and it is the one that gets through review.
- **Validation is not tightened.** A field that becomes mandatory, or a pattern that becomes stricter, breaks old clients.

**For messages, the same plus:**

- **The schema evolution rules of the format**: Avro with a schema registry gives you `BACKWARD` (new consumer reads old data) and `FORWARD` (old consumer reads new data) compatibility; during a rolling deploy you need **`FULL`** - both. Protobuf gives this by construction if you never reuse field numbers and never change types.
- **Consumers must tolerate unknown fields**, and must not fail on a message version they do not recognize.
- **Deploy order matters**: consumers first, then producers, so that no consumer receives a message shape it predates. Reverse it for a removal.
- **Messages are durable**, so a consumer must handle *old* messages already in the topic long after the producer moved on. This is stricter than the API case, where the two versions only coexist for the rollout window.

The enforcement mechanism is **contract tests plus a schema registry with a compatibility policy set to FULL**, checked in CI, so a breaking change fails the build rather than the deployment.

### Q145. Windows, freezes and approval gates

| Control | Reduces risk? | What it actually does |
| --- | --- | --- |
| **Deployment window** (business hours only) | **Yes, genuinely** | Ensures the people who can diagnose and fix are awake and available. This is the one control on the list with a clear causal mechanism. |
| **Change freeze** (peak season, quarter end) | **Mostly moves it** | Nothing ships for four weeks, then a very large batch ships at once - larger, more coupled, harder to bisect and roll back. Risk is deferred and concentrated, not removed. |
| **Manual approval gate** | **Usually moves it** | If the approver has the context to evaluate the change, it is real. If it is a manager approving a diff they cannot read, it is an audit artefact that adds latency and diffuses responsibility. |
| **Peer review on the change** | **Yes** | This is the approval that works, because the approver has context. |
| **Progressive rollout with automated analysis** | **Yes, most of all** | Bounds the blast radius mechanically rather than relying on prediction. |

The framing I would give: risk controls fall into **prediction** (someone judges in advance whether this change is safe) and **containment** (limit exposure and recover fast). Prediction scales badly and degrades into ritual; containment scales and improves with use. Windows work because they support containment - people are available to respond. Freezes and rubber-stamp approvals are prediction controls that mostly relocate risk.

I would keep the deployment window for tier-1 changes, replace the freeze with a **heightened-care period** (canary only, smaller changes, no schema changes, an extra pair of eyes) rather than a total stop, and replace generic approvals with **risk-based** ones - automated for routine changes, human where the change touches money, data or auth.

### Q146. Automated rollback

**Triggers**: the same signals as canary analysis (Q136) - error-rate ratio versus baseline, latency percentile ratio, and a small number of domain metrics - evaluated by the rollout controller. Plus hard triggers: crash-looping pods, readiness never achieved, or an explicit abort.

**How fast**: with a canary controller and a traffic-weighted rollout, shifting weight back to stable is **seconds**, because it is a routing change. The detection is the slow part, and it is bounded by the metric pipeline: scrape interval plus evaluation window plus `failureLimit` consecutive failures, so realistically **1-3 minutes** from onset to abort. Faster is possible with a shorter window at the cost of more false aborts.

**The dangers of fully automatic rollback:**

- **Rollback is not always safe.** If the release included a migration or wrote data in a new format, the automated rollback executes the failure in Q135 - the automation confidently does the unsafe thing. Automatic rollback must be *disabled* for releases that cross a compatibility boundary, and the pipeline should know which those are.
- **Flapping.** A rollout that aborts, is retried automatically, aborts again, produces repeated partial deployments and repeated version churn, which is itself destabilizing. Abort must be terminal until a human intervenes.
- **Misattribution.** The metric degraded because a *downstream dependency* degraded, not because of the new version. The rollback does nothing, and now you have an incident plus a failed deployment plus a team looking at the wrong thing. Comparing against a concurrent baseline (Q136) rather than a historical one mitigates this, because a shared downstream problem affects both.
- **It masks the signal.** If rollbacks are automatic and silent, a service that fails to deploy three times a week looks healthy on the deployment dashboard. Every automatic rollback must page or at minimum create a visible record.
- **The rollback itself is a deployment**, with its own rollout risk, executed by automation under degraded conditions.

My position: **automatic abort of an in-progress rollout, yes** - that is bounded and safe. **Automatic rollback of a fully promoted release, only where compatibility is guaranteed**, and always with a page.

### Q147. Rollback for stateful services and consumer offsets

What is different is that **the state moved forward and the code moving backward has to cope with it.**

**A stateful service** (a StatefulSet with persistent volumes, or a database-backed component):

- **The on-disk format may have changed.** Many stateful systems upgrade their data format on first start and cannot then be downgraded - Elasticsearch, Kafka's inter-broker protocol, most databases. This is a hard, documented constraint, and it is why "roll back the version" is often simply unavailable.
- **The rollout is serial** (Q95), so a rollback is also serial - minutes, not seconds - and a half-rolled-back cluster is running mixed versions, which the system may not support.
- **Quorum and leadership.** Rolling back a majority-quorum system through a mixed-version state can lose the quorum entirely.

**A consumer with a committed offset:**

- The new version consumed messages and **committed offsets past them**. Rolling the code back does not rewind the offset, so those messages are never processed by the old code. If the new version processed them *incorrectly*, the damage is done and rollback does not undo it.
- If you *do* reset the offset to reprocess, everything downstream must be **idempotent**, or you duplicate side effects - double charges, double emails.
- **Consumer group rebalancing** during the rollback causes another round of partition reassignment and potential duplicate processing.
- If the new version wrote to an output topic in a new format, downstream consumers have already seen it.

**What you plan in advance:**

1. **Decide the rollback strategy before the release**, and write it down: is this release rollback-safe, roll-forward-only, or does it need a restore?
2. **Keep the data format compatible for at least one version**, the same expand-contract discipline as the schema.
3. **Make consumers idempotent** as a standing property, so offset resets are survivable.
4. **Record the offset (and any relevant state markers) at the start of the deployment**, so a reset is possible and precise.
5. **Prefer a kill switch to a rollback**: a flag that makes the new code path behave as the old one avoids all of this, because the binary never changes.
6. **Rehearse it.** For stateful systems, the rollback path must be tested in staging with representative data, because it is the path most likely to be impossible.

### Q148. Two-week manual UAT gate `[A]`

**Understand what the gate is buying first**, because it is not irrational - it exists because someone was burned. Usually it is providing one of three things: (a) confidence that the change works, because automated coverage is not trusted; (b) a business sign-off that the change is what was asked for; (c) a compliance control requiring documented approval by a named person. These need completely different responses, and attacking the gate without knowing which is a fast way to lose.

**The case for change**, framed in their terms rather than as a DevOps principle:

- **The gate does not do what it claims.** Two weeks of manual UAT on a batch of changes tests a fraction of the behaviour, in an environment that is not production, against data that is not production data. Quantify it: how many production incidents in the last year were *caught* by UAT, versus how many got through? That number is usually devastating and it is the strongest argument available.
- **The gate creates the risk it is trying to prevent.** A two-week gate forces batching: a fortnight of changes ships at once, so when something breaks you have fifty candidate causes and no ability to bisect. Smaller, more frequent releases are safer, and the gate makes them impossible.
- **It lengthens MTTR.** A fix for a production incident must also pass the gate, or the gate is bypassed - and a bypassed control is not a control.

**The transition I would actually run** - incremental, never a big-bang removal:

1. **Instrument first.** Measure change lead time, batch size, escaped defects, and which UAT findings were real. Do this for two months before proposing anything. Data beats principle in this conversation.
2. **Build the replacement before removing the gate.** Automated contract and end-to-end tests covering the scenarios UAT actually exercises - derived from the UAT scripts themselves, which makes it concrete and gives the UAT team ownership of the replacement. Then progressive rollout with automated analysis, and a fast, tested rollback.
3. **Make the case with a pilot.** One low-risk service moves to a shorter gate - say, two days - with the automated evidence attached. Run it for a quarter and compare defect rates. One team's data is worth more than any argument.
4. **Reframe rather than remove.** Propose that UAT moves *left* (testers involved during development, testing in a shared environment continuously) and that the gate becomes **risk-based**: routine changes go through automation, changes touching money, data or regulated functions keep a human gate. This lets the control stay in place where it is defensible and disappear where it is theatre.
5. **Satisfy compliance differently, not less.** If the gate is a documented control, replace it with a *stronger* automated one - signed provenance, an audit trail of every check, evidence generated by the pipeline (Q246). Auditors generally prefer automated evidence to a spreadsheet; the conversation to have is with the auditor, not around them.
6. **Keep a lever they control.** A change freeze on demand, or the ability to require a manual gate for a specific release, means the business is giving up latency rather than control - which is usually the real objection.

**What I would not do**: declare the gate stupid, remove it unilaterally, or promise it will be fine. If a release goes badly in month two of this transition, the gate comes back for three years.

*Hook: a manual gate you replaced, and the number you used to make the argument.*

---

## 10. GitOps and Argo CD

### Q149. GitOps by its properties

Four properties, independent of tooling:

1. **Declarative** - the entire desired state of the system is expressed declaratively, not as a sequence of commands.
2. **Versioned and immutable** - that declaration lives in a versioned store (git), so every state the system has ever been asked to be in is recoverable and attributable.
3. **Pulled automatically** - an agent in the target environment retrieves the desired state; nothing pushes into the cluster.
4. **Continuously reconciled** - the agent compares desired to actual continuously and corrects the difference, so drift is detected and (optionally) repaired.

**Compared with a pipeline running `kubectl apply`:**

- The pipeline is a **push at a point in time**. Between deployments, nothing checks that the cluster still matches. A manual change, a controller mutation or a deleted resource persists silently until someone notices. GitOps reconciles continuously, so the cluster's state is an *observable* rather than an assumption.
- The pipeline needs **credentials to the cluster**, from outside the cluster. That is the security difference (Q150).
- **`kubectl apply` succeeding means the API server accepted the object**, not that it became healthy. A GitOps controller tracks health as a first-class concept.
- **Recovery.** Rebuilding a cluster from a pipeline means re-running every pipeline in the right order. From a GitOps repository it means pointing an agent at the repository.
- **The audit trail is the git history** rather than a set of CI job logs that expire.

The property that is most often missed: **git is the source of truth, so a change made any other way is by definition drift.** That is the discipline, and it is harder than the tooling.

### Q150. Push versus pull

**Push**: CI holds credentials for the target and applies changes. **Pull**: an agent inside the target watches a repository and applies changes itself.

**The security property pull buys you**: no credentials to the cluster exist outside the cluster. In a push model, the CI system holds a kubeconfig or a cloud role that can deploy to production, which means **CI is in the production trust boundary** - compromise the build system and you own production (Q245). In a pull model the agent's credentials never leave the cluster, and the cluster's inbound firewall needs no path from CI at all. This also means clusters in private networks, or in customer environments, need no ingress.

The related property: the agent only ever needs **read access to the repository**, so the credential CI holds is a git write credential, which is far less dangerous than a cluster-admin kubeconfig.

**What it costs operationally:**

- **Loss of synchronous feedback.** A push pipeline reports success or failure inline. With pull, CI's job ends at "commit merged" and the deployment result is somewhere else, so you need to bridge that back - which people do badly, and which is why "did it deploy?" becomes an unanswered question.
- **An extra hop and an extra latency**, bounded by the reconciliation interval or the webhook.
- **Another component to operate**, which must be highly available, and whose own upgrade is a delicate operation because it deploys everything else.
- **Orchestration across systems is harder.** "Deploy this, then run this migration, then notify that" is natural in a pipeline and awkward in a reconciler. Sync waves and hooks (Q152) cover a lot, but not everything.
- **Secrets need a different story**, because the repository cannot hold them (Q160).

The pragmatic middle used widely: pull-based reconciliation for the deployment, with the pipeline **waiting on and reporting the reconciliation result** via the agent's API, so you keep the security property and the feedback loop.

### Q151. Argo CD architecture

Three components:

- **API server** - serves the UI, CLI and API. Handles authentication, RBAC, and the Application CRUD. It is not in the reconciliation path.
- **Repo server** - clones and caches git repositories, and **renders manifests**: runs `helm template`, `kustomize build`, a config management plugin, or plain YAML. It has no cluster access. It is stateless and is the component you scale when rendering is slow.
- **Application controller** - the reconciliation loop. For each Application it fetches the rendered desired state from the repo server, fetches the live state from the target cluster (via a cached, watch-backed informer over all managed resources), computes the diff, reports `Synced`/`OutOfSync`, assesses health, and - if configured - applies the difference.

Plus **Redis** as a cache for rendered manifests and cluster state, and optionally **ApplicationSet controller** for generating Applications.

**Where reconciliation happens**: in the application controller, and **what it compares is the rendered desired manifest against the live object in the cluster**, field by field, with normalizations. Specifically it diffs the *desired* fields against the live object using either a three-way merge against the `last-applied-configuration` annotation, or - with server-side apply - against the fields owned by Argo CD's field manager. That distinction matters: Argo CD does not care about fields it does not manage, which is how it coexists with mutating webhooks and HPAs (mostly - see Q155).

The reconciliation is triggered by a **timer** (`timeout.reconciliation`, 3 minutes by default), by a **git webhook**, or by a **cluster event** on a managed resource.

### Q152. Sync waves, hooks and health

**Sync waves**: the annotation `argocd.argoproj.io/sync-wave: "-1"` puts a resource in an ordered group. Argo CD applies all resources in wave *n*, waits for them to be **healthy**, then proceeds to wave *n+1*. Default is 0. Within a wave there is also an implicit kind ordering (namespaces and CRDs before the things that use them). This is how you express "CRDs, then the operator, then the custom resources".

**Hooks**: `argocd.argoproj.io/hook: PreSync | Sync | PostSync | SyncFail | Skip`. A PreSync hook - typically a Job running a database migration - must complete successfully before the main sync proceeds. `hook-delete-policy` controls cleanup. This is Argo CD's answer to the "pipelines can orchestrate, reconcilers cannot" objection.

**Health assessment** is the important part of the question. `Synced` and `Healthy` are **orthogonal**:

- **`Synced`** means: the live state matches the desired state in git. It is a *diff* result.
- **`Healthy`** means: the resources report themselves as working, per a per-kind health check.

Argo CD ships built-in health checks for the standard kinds - a Deployment is Healthy when its `status` shows the observed generation matches, the updated replicas equal the desired, and available replicas are sufficient; a Service of type LoadBalancer is Healthy when it has an ingress IP; a PVC when it is `Bound`; an Ingress when the load balancer is provisioned. For CRDs, you write a **Lua health check** - which is how you teach Argo CD that a `Rollout` is only Healthy when fully promoted, or that a `Certificate` is Healthy when issued.

The Application's aggregate health is the worst health of its resources, with `Progressing` while a rollout is in flight. So `Synced` + `Healthy` means "git matches the cluster, and Kubernetes' own controllers say those objects are working".

### Q153. Synced and Healthy while returning 500s `[T]`

**What Argo CD knows**: that the objects in the cluster match the YAML in git, and that the *controllers responsible for those objects* report them as satisfied. For a Deployment, "Healthy" resolves to: the ReplicaSet rolled out, the desired number of pods exist, and they are **Ready** - which means their **readiness probes pass**.

**What it does not know**:

- **Whether the application is correct.** It has no notion of the service's error rate, latency, or business function. Health is Kubernetes' opinion of the pod, and Kubernetes' opinion is your readiness probe's opinion (Q86, Q87).
- **Whether the configuration is right.** A ConfigMap pointing at the wrong database is `Synced` (it matches git) and `Healthy` (it is a ConfigMap; ConfigMaps are always healthy). The pods start, pass their probes, and fail every request.
- **Anything outside its Application.** A missing secret in another namespace, a downstream service, a network policy, a DNS problem, an expired certificate on an external dependency, a database that is down.
- **Whether git is right.** If someone committed the wrong image tag, Argo CD faithfully and successfully deploys the wrong thing, and reports success. GitOps guarantees the cluster matches git; it guarantees nothing about git.
- **Runtime behaviour after readiness.** The pod passed at second 20 and started failing at second 90.

The design conclusion: **Argo CD is a state-convergence tool, not a release-verification tool.** Release verification requires service-level signals, which is what Argo Rollouts adds (Q137) - and this is exactly why the two exist as separate products. In a mature setup, `Synced` and `Healthy` gate the *rollout controller*, and the rollout controller gates on SLIs.

### Q154. Drift detection and self-heal

**Drift detection** is always on: the controller compares live to desired every reconciliation and marks the Application `OutOfSync` when they differ. **Self-heal** (`syncPolicy.automated.selfHeal: true`) additionally re-applies the desired state, so manual changes are reverted within a reconciliation cycle.

Self-heal is the correct default for production: it makes git genuinely authoritative, it removes the entire class of "someone hotfixed the cluster and nobody knows", and it means a cluster rebuild is deterministic.

**When I would deliberately leave it off:**

1. **During an incident**, temporarily. If an engineer needs to scale a deployment or patch a resource at 3 am, self-heal will fight them and the fight is not a good use of an incident. The correct pattern is a documented break-glass: disable self-heal (or add a temporary `ignoreDifferences`), make the change, then reconcile git to reality afterwards. Leaving it on and forcing every emergency change through a PR sounds pure and produces people disabling the controller instead.
2. **Where another controller legitimately owns a field.** An HPA owns `spec.replicas`; a VPA owns resource requests; a mutating webhook owns injected sidecars; a cloud controller owns Service annotations. Rather than turning self-heal off wholesale, the right answer is `ignoreDifferences` on those specific fields - but if the overlap is extensive, off is pragmatic (Q155).
3. **During a migration onto GitOps**, where the cluster's current state is not yet fully represented in git. Turning self-heal on early deletes things you did not know existed.
4. **In development or experimentation environments**, where the ability to poke at the cluster is the point and the cost of drift is zero.
5. **For resources managed by an operator** that mutates its own CRs - the operator writing status or defaults into the spec is not drift, it is the operator working.

The important discipline: **self-heal off means drift must still be alerted on.** A permanently `OutOfSync` Application that nobody looks at is worse than either extreme, because it destroys the signal.

### Q155. Operator mutation causing a permanent sync loop `[T]`

**Mechanism.** Argo CD renders the desired manifest from git and diffs it against the live object. Another controller - a mutating webhook, an operator, an HPA, or the API server's defaulting - writes a field into the live object that is not in git. Argo CD sees a difference, marks it `OutOfSync`, and with self-heal enabled re-applies the git version, removing the field. The other controller immediately writes it back. Round and round: continuous API writes, resource version churn, controller CPU burn, an Application that flaps between Synced and OutOfSync, and - in the worst case - repeated pod restarts because the mutated field is in the pod template.

Common instances: an HPA setting `spec.replicas` while `replicas` is also in git; a service mesh injecting a sidecar container; `kubectl.kubernetes.io/last-applied-configuration` interactions; a cloud load balancer controller writing annotations; cert-manager populating a Secret; an operator normalizing its own CR spec.

**Three ways to resolve it:**

1. **`ignoreDifferences`** - tell Argo CD not to diff specific fields, by JSON pointer or JQ path expression:

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers: ["/spec/replicas"]
    - group: apps
      kind: Deployment
      jqPathExpressions: ['.spec.template.spec.containers[] | select(.name == "istio-proxy")']
```

This is the surgical fix. Note `ignoreDifferences` affects the *diff*, not the *apply* - for it to also stop the field being overwritten during a sync you need `RespectIgnoreDifferences=true` in the sync options.

2. **Remove the field from git.** If the HPA owns replicas, `replicas` should not be in the manifest at all. This is the cleanest answer whenever there is a genuine single owner, and it is usually the right one - the sync loop is a symptom of two systems claiming the same field.

3. **Server-side apply with field management.** `syncOptions: [ServerSideApply=true]` makes Argo CD a named field manager, so it only asserts ownership of the fields it actually sets and yields fields owned by other managers. This solves the general case structurally rather than field by field, and is the direction I would take an estate with many operators.

A fourth, blunter option: disable self-heal for that Application (Q154), which stops the loop and gives up the guarantee.

### Q156. GitOps repository structure

The decision that matters is **separating application source from deployment manifests**, and I do separate them.

**Why separate repositories:**

- **A manifest commit is a deployment.** If manifests live with source, every source commit touches the deployment repository's history and you cannot tell a code change from a release. Separation makes the deployment repository's history a clean, auditable record of what was released, when, by whom.
- **Different access control.** Production manifests can require different reviewers - the platform team, or a change-approval group - without applying that to application code.
- **No infinite loop.** If the image-updating automation writes back to the same repository that triggers CI, you get a build loop unless you carefully exclude paths.
- **Environments are not branches of code.** The production manifest set has no meaningful relationship to a source branch.

**Structure I would use** - one deployment repository per environment or per cluster, with a directory per application:

```
deploy-prod/
  apps/
    orders/
      kustomization.yaml       # references base + sets image digest
    payments/
  platform/
    ingress-nginx/
    cert-manager/
```

with a shared `deploy-base` repository holding the per-service base manifests, referenced by the environment overlays. The alternative - one repository with a directory per environment - is simpler and fine for a small estate; the argument for splitting by environment is that it lets you give production its own protection rules and its own blast radius.

**What it does to the review flow**: promoting to production becomes a small, readable pull request that changes an image digest and nothing else - which is exactly the diff you want a reviewer to see, and a far better artefact than "approve this deployment" in a CI tool. The cost is two pull requests per change (code, then promotion), which is why the promotion PR should be opened automatically by the pipeline.

### Q157. Environment promotion without copy-paste

| | Mechanism | Strength | Weakness |
| --- | --- | --- | --- |
| **Kustomize overlays** | A `base/` with common manifests; per-environment overlays applying strategic-merge and JSON patches | Fully declarative, the output is plain YAML, no templating language, the diff between environments is *literally the overlay* - which is the best possible artefact for reviewing drift (Q129) | Patches become hard to follow when they are deep or numerous; no conditionals or loops, so genuinely variable structure is awkward |
| **Helm values hierarchies** | One chart, `values.yaml` plus `values-prod.yaml` layered | Handles conditional and repeated structure well; the ecosystem standard for third-party software | The rendered output is not visible in git, so review is of *inputs* not results; template logic accretes; values files drift into containing logic |
| **ApplicationSets** | A generator (list, git directory, cluster, matrix) produces Argo CD Applications from a template | Removes the copy-paste of the *Application* objects themselves - the thing that otherwise multiplies by environments × services | It does not solve manifest variation; it solves Application variation. It is complementary, not an alternative |

**What I actually run**: a Kustomize base per service with thin per-environment overlays containing only what must differ (Q129), Helm for third-party components where the chart is the vendor's interface, and an ApplicationSet with a git-directory generator so that adding a service directory automatically creates its Applications across environments. Rendering Helm through Kustomize (`helmCharts` in a kustomization) lets you patch a vendor chart without forking it, which is the practical way to combine them.

The rule that keeps this honest: **the overlay contains values, never logic**, and the set of keys an overlay may contain is enumerable and linted.

### Q158. Helm versus Kustomize

**Helm templates**: a chart is Go templates rendered with values. It has conditionals, loops, functions, a dependency mechanism and a release lifecycle with hooks.

**Kustomize patches**: a base of valid YAML, modified by strategic-merge and JSON patches. No templating language; the input is always valid Kubernetes YAML.

**What each gets wrong:**

- **Helm's mistake is that it is string templating over a structured format.** The template is not YAML until it is rendered, so indentation bugs are a whole class of error, the editor cannot help you, and a complex chart becomes unreadable. Values files grow into a poorly-specified configuration language with no schema (`values.schema.json` helps and is under-used). And because the rendered output is not in git, review is indirect.
- **Kustomize's mistake is that it has no escape hatch.** The moment you need a conditional, a loop, or a value in three places, you are patching around the limitation. Deep patches on nested structures (containers by name, env vars by name) are fiddly and fragile, and a stack of overlays becomes as hard to trace as a template.

**Can you defensibly use both? Yes, and it is common.** The pattern: use Helm for third-party software, because the chart is how vendors ship and forking it is worse; use Kustomize for your own services, because your services do not need templating and the reviewable-plain-YAML property is worth a lot. Where you need to modify a vendor chart, render it through Kustomize (`helmCharts` in a `kustomization.yaml`, or `helm template | kustomize`) and patch the output rather than forking.

What is *not* defensible is using both for the same manifests in an ad-hoc way, so nobody can tell where a value comes from. The rule should be stated and consistent.

### Q159. Image updates in GitOps

The image tag or digest in the manifest repository has to change, and something must write it. Three mechanisms:

1. **CI writes back.** After building and pushing, the pipeline clones the manifest repository, updates the digest (with `kustomize edit set image` or `yq`), commits and pushes - or, better, **opens a pull request**. This is explicit and reviewable.
2. **Argo CD Image Updater** (or Flux's image automation controller) polls the registry for new tags matching a policy, and writes the update back to git itself. No CI credentials to the manifest repository, but the update is triggered by a registry state rather than by a build event.
3. **An intermediate promotion tool** (Kargo, or an in-house promoter) that models environments as stages and moves a "freight" of artifacts through them with policy at each boundary.

**What the write-back creates that you must plan for:**

- **A bot identity with write access to the deployment repository.** That credential is now a production-deployment credential and must be scoped, protected and audited accordingly. This is where the "GitOps removed cluster credentials from CI" property gets partially given back, and it is worth being honest about.
- **Commit noise.** Every build produces a commit in the manifest repository, so its history fills with bot commits. Mitigate by committing digests only on promotion, not on every build, and by using a distinct bot author so history can be filtered.
- **Loops.** If the manifest repository triggers CI, a bot commit triggers a build which makes a bot commit. Path filters, `[skip ci]` markers, or repository separation (Q156) prevent it.
- **Race conditions.** Two services promoting simultaneously produce a push conflict. The writer needs retry-with-rebase.
- **A bypass of branch protection**, if the bot pushes directly to a protected branch. Either grant the bot an exception (and accept it) or have it open a PR that a human or an auto-merge rule approves. For production I prefer the PR, because the promotion diff is the release record.
- **Rollback semantics.** Reverting the promotion commit is the rollback, which is clean - but only if the commit contains *only* the promotion.

### Q160. Secrets in a GitOps repository

**Approach 1 - Sealed Secrets (encrypted in git).** What is stored in git: a `SealedSecret` custom resource containing the **ciphertext**, encrypted with the public half of a key pair whose private half lives only in the controller in the cluster. Nothing readable is in git, and the encryption is per-namespace-and-name by default, so a sealed secret cannot be moved to another namespace to be decrypted. The controller decrypts and creates a normal Secret.
- Pros: fully self-contained, no external dependency, the secret's *existence and shape* is visible in git which is good for review.
- Cons: rotation requires re-sealing and committing; the plaintext ends up in etcd anyway; losing the controller's private key loses every secret; and an encrypted blob in git is still a blob an attacker can take away and attack offline forever.

**Approach 2 - External Secrets Operator (reference in git).** What is stored in git: an `ExternalSecret` resource containing **only a reference** - the store name, the remote key path, and the mapping to fields in the resulting Kubernetes Secret. No ciphertext, no plaintext. The operator authenticates to the external store using workload identity and creates the Secret.

```yaml
kind: ExternalSecret
spec:
  secretStoreRef: { name: aws-secrets, kind: ClusterSecretStore }
  target: { name: orders-db }
  data:
    - secretKey: password
      remoteRef: { key: /prod/orders/db, property: password }
```

- Pros: rotation happens in the store with no git commit at all; git contains nothing sensitive even in encrypted form; one system of record shared with non-Kubernetes consumers (Q131); real audit logging of secret access.
- Cons: a runtime dependency on the external store; the plaintext still lands in etcd (use the CSI driver if that matters); and the actual secret value is invisible to reviewers, which is a genuine trade-off - you cannot review what you cannot see.

**Which I choose**: External Secrets, for the rotation property alone. Sealed Secrets is a reasonable answer for an estate with no external store yet.

### Q161. Multi-cluster Argo CD

**Hub-and-spoke**: one Argo CD instance in a management cluster, with credentials to every target cluster.

- **Blast radius**: the hub is a single point of failure for *deployment* across the estate (running workloads are unaffected - Q81's distinction applies). A hub compromise is a compromise of every cluster.
- **Credentials**: the hub holds a kubeconfig or a role per target cluster, which reintroduces exactly the cross-boundary credential that pull-based GitOps was meant to remove. Mitigations exist (per-cluster roles scoped to specific namespaces, network restrictions), but the hub is unambiguously a tier-0 system.
- **Scale**: the application controller maintains **informers watching every managed resource in every cluster**. Memory and CPU scale with total object count across the estate, and this is the real limit - a few thousand Applications and tens of thousands of resources is where tuning starts (sharding the controller by cluster with `ARGOCD_CONTROLLER_REPLICAS`, `--repo-server-timeout`, resource exclusions to stop watching irrelevant kinds).
- **Benefit**: one place to look, one RBAC model, one set of ApplicationSets generating across clusters, one upgrade.

**Per-cluster instances**: an Argo CD in each cluster managing only itself.

- **Blast radius**: contained. One instance's failure or compromise affects one cluster.
- **Credentials**: none leave the cluster. The purest form of the pull model.
- **Scale**: trivially horizontal - each instance only watches its own cluster.
- **Cost**: N instances to run, upgrade and monitor; no single view of the estate; ApplicationSets and shared configuration must be duplicated or generated.

**What I would run**: **per-cluster instances for production clusters**, because the credential and blast-radius properties are the whole point of GitOps and production is where they matter; a **hub for non-production** where the operational saving outweighs the risk. If a single view of production is a hard requirement, use per-cluster instances plus an aggregating dashboard rather than giving one instance credentials to everything.

### Q162. GitOps with a compliance approval gate `[A]`

The instinct is to put a human approval in front of the reconciler, which fights the model. The correct design is to **make the approval a property of the git state**, so the reconciler needs no gate at all.

**The flow:**

1. **CI builds, signs and publishes the artifact**, and generates provenance. No cluster access.
2. **Promotion to production is a pull request** against the production manifest repository, opened automatically by the pipeline, changing only the image digest. This PR *is* the change record.
3. **The approval is the PR approval**, enforced by branch protection: required reviewers from a designated group (CODEOWNERS on the production directory), no self-approval, dismiss stale approvals, and signed commits so the approver's identity is cryptographically attested.
4. **Merge to the production branch is the authorization event.** Argo CD watches only that branch, with automated sync and self-heal enabled. It never needs to know about approval - it deploys what is approved, because only approved things are on the branch.
5. **Evidence** is generated automatically: the PR record (who approved, when, what diff), the linked build provenance, the CI check results, and the Argo CD sync record with the resulting resource versions. That set answers every question a change-control auditor asks, and it is produced by the system rather than assembled by a person (Q246).

**Why this satisfies compliance better than a deployment gate:** the control is *preventive* (nothing unapproved can reach the branch) rather than *detective*, the evidence is tamper-evident (git history, signed commits, transparency log), and separation of duties is enforceable - the author cannot approve, and the approver cannot bypass branch protection (Q247).

**If they insist on a gate at deployment time** - because the control is written as "deployment requires approval" rather than "changes require approval" - the options are: Argo CD's **sync windows** (deployment only permitted in defined periods), **manual sync** for the production Application with sync permission granted to the approval group via Argo RBAC, or a **PreSync hook** that blocks on an external approval system. I would use manual sync as the compromise, because it keeps the reconciliation model intact and puts the gate on a single, auditable action.

**The conversation to have** is with the auditor, not around them: the control objective is "no unauthorized change reaches production", and a merge-gated GitOps flow satisfies it more rigorously than a click-through approval on a deployment tool. That argument usually lands, and it lands much better when you bring the evidence artefacts to the meeting.

*Hook: a compliance control you re-implemented in the pipeline and how you got it accepted.*

---

## 11. Infrastructure as Code and Terraform

### Q163. Declarative versus imperative

An **imperative** script says *how*: create this, then that, then configure the other. It is a sequence of actions, and it is only correct when run against the state the author imagined.

A **declarative** desired-state tool says *what*: this is the set of resources and their properties. The tool computes the actions by diffing desired against actual.

**What that buys you:**

1. **Idempotence.** Running it twice is the same as running it once, because the second run finds no difference. A provisioning script has to be written defensively to achieve this, and rarely is.
2. **Convergence from an unknown state.** You do not need to know what exists; the tool discovers and reconciles. A script that assumes nothing exists fails on a partially-created environment - which is exactly the state you are in after a failure.
3. **A plan.** You can see the actions before they happen, review them, and gate on them. This is the single most valuable operational property and a script cannot offer it.
4. **Drift detection.** Because desired state is written down, deviation is computable (Q166).
5. **The code is the documentation.** It describes the infrastructure rather than the steps someone took, which is what a reader actually needs.
6. **Dependency ordering is derived**, not hand-maintained. The tool builds a graph from references and parallelizes safely.

The cost is that you inherit the tool's model of the world: anything the provider does not express, you cannot declare, and escaping to imperative behaviour (`local-exec`, `null_resource`) discards every property above.

### Q164. Terraform state

**What is in it**: a JSON document mapping each resource address in your configuration (`aws_instance.web[0]`) to the **real-world object's identifier** and a full snapshot of its attributes as of the last apply, plus the dependency graph, the provider configuration used, output values, and a serial number and lineage for concurrency control.

**Why it is required:**

1. **Binding.** Nothing in AWS records "this instance is `aws_instance.web`". State is the only mapping between a configuration address and a real object ID. Without it, Terraform cannot know whether to create or update.
2. **Deletion detection.** Removing a resource block means Terraform must destroy it - which requires knowing it once existed. A pure refresh-and-compare against the cloud cannot distinguish "I do not manage this" from "I should delete this".
3. **Performance.** The stored attributes let Terraform plan without reading every resource, which matters at scale.
4. **Metadata refresh does not preserve** - some attributes are not readable back from the API (a generated password, a write-only field), so the state is the only record.

**Concurrent runs on the same state** are the classic disaster: both read the same state, both plan against it, both apply, and the last writer's state overwrites the first's. The result is a state file that does not describe reality - resources created by the first run are now **orphaned** (real but unmanaged), and the next plan proposes to create them again, which either fails on a name conflict or duplicates infrastructure. Worse combinations produce a plan that destroys resources that are actually in use. This is why locking (Q165) is not optional.

### Q165. Remote state with locking

**The backend**: state stored in S3 (versioned, encrypted, with public access blocked), with a lock held in DynamoDB.

**The lock mechanism**: before any operation that reads or writes state, Terraform writes an item to the DynamoDB table with the state file's path as the partition key, using a **conditional put** (`attribute_not_exists(LockID)`). DynamoDB's conditional write is atomic, so exactly one writer wins. The item contains the lock ID, who holds it, the operation, and a timestamp. On completion Terraform deletes the item. A second run finds the item present, fails the conditional write, and blocks (or fails with `-lock-timeout=0`).

State integrity is separately protected by a **digest** of the state stored in the same table, so Terraform can detect that S3 returned a stale object under eventual consistency.

(Worth knowing: since Terraform 1.10, S3 supports native locking via a `.tflock` object with conditional writes, so the DynamoDB table is no longer required. The mechanism is the same idea.)

**When a lock is stuck** - a run was killed, a CI job was cancelled, a laptop closed mid-apply:

1. **Find out why.** `terraform plan` reports the lock ID, who holds it, and when it was acquired. Check whether that run is genuinely dead - a lock held by a *running* apply must never be broken.
2. **Confirm the apply is not in flight.** Look at the CI job. If an apply is halfway through, breaking the lock and starting another run is how you get Q176 plus Q164 simultaneously.
3. **`terraform force-unlock <LOCK_ID>`**, which deletes the DynamoDB item. Never delete the item by hand unless Terraform cannot.
4. **Then verify state integrity**: run a plan and read it carefully. A killed apply may have created resources not recorded in state (Q176).

The guardrail: CI jobs running `apply` should have a **timeout shorter than the human patience threshold** and should trap termination signals so the lock is released, and there should be an alert on locks older than an hour.

### Q166. Console change caused drift `[T]`

**What the tools actually do:**

- **`terraform plan`** already refreshes by default: it reads each managed resource from the provider and compares. So the console change shows up as a diff, and a plain `apply` would **revert it**. That is often the right answer - the configuration is the source of truth - and it is the default behaviour, so the first question is whether reverting is safe.
- **`terraform plan -refresh-only`** (and `apply -refresh-only`) compares real state to *stored state* and updates the **state file** to match reality, without changing infrastructure and without proposing configuration changes. This is how you **accept** a drift: adopt reality into state, then decide separately whether to update the configuration to match. It replaced the deprecated `terraform refresh`, whose problem was that it wrote state with no plan and no approval.
- **`terraform import`** binds an **unmanaged** real resource to a configuration address, writing it into state. It does not generate configuration (though `terraform plan -generate-config-out` can now produce a starting point). It is for resources Terraform never created, not for drift on resources it did.

**My options, in order:**

1. **Revert it.** Run `terraform apply` and let the configuration win. Correct when the console change was unauthorized or wrong. Read the plan first - a revert can be destructive.
2. **Adopt it.** If the change was legitimate and should persist, update the **configuration** to match, then `apply` and confirm a no-op plan. This is the honest resolution: the code now describes reality.
3. **Adopt into state only** with `-refresh-only`, as a stop-gap when you need state to be accurate now and will fix the configuration shortly. Leaving it here is how drift becomes permanent.
4. **Ignore it deliberately** with `lifecycle { ignore_changes = [tags["LastModified"], desired_count] }` where another system legitimately owns the field - the Terraform equivalent of Argo CD's `ignoreDifferences` (Q155). Autoscaling group desired capacity is the canonical example.
5. **Import**, if the change created a *new* resource rather than modifying one.

**The systemic fix** is to remove console write access in production and run a scheduled `plan` that alerts on any non-empty diff, so drift is detected within a day rather than discovered during an unrelated change.

### Q167. State blast radius

**How to split**: by **lifecycle and blast radius**, not by resource type or by team org chart. Things that change together and fail together belong in one state; things with different change rates belong apart.

A layering that works:

| Layer | Change rate | Contents |
| --- | --- | --- |
| **Foundation** | Yearly | Accounts, VPCs, subnets, transit gateway, DNS zones, IAM roles |
| **Platform** | Monthly | EKS cluster, node groups, shared databases, shared caches, observability stack |
| **Application** | Daily/weekly | Per-service resources: queues, buckets, IAM roles, DNS records |

with one state per layer per environment per region, and cross-layer references by **data source** or **remote state output** (Q172).

**The trade-off:**

| | One big state | Many small states |
| --- | --- | --- |
| **Blast radius** | Terrible - one bad apply can destroy the estate; one corrupted state file is total | Contained; a failure affects one component |
| **Plan time** | Grows to tens of minutes as the refresh reads thousands of resources; nobody reads a 4,000-line plan | Seconds to a minute; a reviewable plan |
| **Lock contention** | Every change queues behind every other; at 20 engineers this is the daily pain | Parallel work |
| **Dependency handling** | Automatic and correct - the graph spans everything | Manual: you must order applies and manage cross-state references |
| **Refactoring** | Free - move resources between modules within one state | Painful - moving a resource between states requires `terraform state mv` across backends or import/remove |
| **Consistency** | A single apply is atomic-ish across everything | Partial application across states is normal, so you need convergence discipline |

The failure mode of over-splitting is a distributed monolith of states with a hand-maintained apply order and a web of remote-state dependencies - which is Q172's problem. The failure mode of under-splitting is a 40-minute plan nobody reads and a lock everyone waits on. Three or four layers is usually right.

### Q168. count versus for_each

**`count`** produces resources indexed by **position**: `aws_instance.web[0]`, `[1]`, `[2]`. The state key is the integer.

**`for_each`** produces resources indexed by **a stable key** from a map or set: `aws_instance.web["api"]`, `["worker"]`. The state key is the string.

**Why removing a middle element from a `count` list is destructive**: given `count = length(var.names)` with `["a", "b", "c"]`, state holds `[0]→a, [1]→b, [2]→c`. Remove `"b"`, and the list becomes `["a", "c"]`. Terraform now computes: index 0 should be `a` (unchanged), index 1 should be `c` but state says it is `b` → **update in place, or destroy and recreate** depending on whether the changed attribute forces replacement; index 2 no longer exists → **destroy**. So removing one element rewrites every resource after it. For an instance with a name that forces replacement, that is a rebuild of the tail of the list.

**`for_each` changes it** because identity is the key, not the position. Removing `"b"` from the map leaves `["a"]` and `["c"]` untouched and destroys only `["b"]`. The plan is exactly what you intended.

**Rule**: use `for_each` for anything where the elements have identity - named environments, subnets per AZ, IAM policies per role, records per hostname. Use `count` only for genuinely homogeneous, interchangeable replicas, or as a conditional (`count = var.enabled ? 1 : 0`), which is its other idiomatic use. And note that `for_each` keys must be known at plan time, which is the constraint that occasionally forces you back to `count`.

### Q169. A module rename destroyed 40 resources `[T]`

**Mechanism.** A resource's identity in state is its **address**: `module.networking.aws_subnet.private[0]`. Renaming the module changes the address to `module.network.aws_subnet.private[0]`. Terraform does not track the rename - it sees an address in state with no corresponding block in the configuration (→ **destroy**) and a block in the configuration with no corresponding state entry (→ **create**). Multiply by 40 resources.

The same happens for renaming a resource block, moving a resource into or out of a module, or changing a `count` to a `for_each` (which changes every index from an integer to a string key).

**Two remedies:**

1. **`moved` blocks** - the modern, correct answer. Declare the rename in configuration:

```hcl
moved {
  from = module.networking
  to   = module.network
}
```

Terraform reads these during planning and rewrites the state addresses itself, producing a no-op plan. They are **declarative, reviewable in the PR, and version-controlled**, so every consumer of a shared module gets the rename handled automatically - which is why they matter for published modules. They can be removed once every consumer has applied.

2. **`terraform state mv`** - the imperative equivalent, run once against the backend:

```
terraform state mv module.networking.aws_subnet.private[0] module.network.aws_subnet.private[0]
```

It works, and it is what existed before `moved` blocks, but it is a manual out-of-band mutation of state that is not reviewed, not repeatable, and must be run by every operator of every state that consumes the module. Use it for one-off local fixes, not for a change you are shipping.

**The process control**: nobody applies a plan without reading it, and CI should **fail any plan containing a destroy** unless a specific label or approval is present. A 40-resource destroy should never have got as far as being possible to apply by accident.

*Hook: a plan that proposed a destroy you caught in review.*

### Q170. Module design

**What makes a module reusable:**

- **It has a clear, single responsibility** and a small interface. A module that takes 60 variables is a copy of your configuration with extra steps.
- **Sensible defaults** for everything optional, so the common case is three inputs.
- **Opinionated on the things that should be consistent** - tagging, encryption, logging, naming convention - and configurable on the things that genuinely vary. A module's value is largely that it encodes the decisions you do not want re-litigated.
- **Outputs everything a consumer might need to reference**, because a consumer who cannot get an ARN out will reach around the module with a data source, and the encapsulation is gone.
- **Variable validation** (`validation` blocks) and typed variables, so misuse fails at plan time with a useful message.
- **It does not configure providers.** A module with a `provider` block cannot be used with `for_each` and creates a permanent dependency; providers are passed in.
- **Documented**, ideally generated (`terraform-docs`), with an example.

**Never hardcoded**: account IDs, region, AMI IDs, CIDR blocks, names, tags, and anything environment-specific. Also: no hardcoded provider aliases, no hardcoded backend, and no `depends_on` to a specific external resource.

**Versioning and consumption across teams:**

- **A separate repository per module** (or a monorepo with per-module tags), published with **semantic version tags**.
- **Consumers pin an exact version**: `source = "git::...//modules/vpc?ref=v2.3.1"` or a registry reference with `version = "~> 2.3"`. Never a branch - that is a live edit to everyone's infrastructure.
- **Semver means something**: a change that forces resource replacement is a **major**, even if the interface is unchanged. This is the rule people get wrong, and it is the one that matters, because a minor bump that recreates a database is an outage.
- **A changelog stating the plan impact** of each version: "this version adds a tag; expect an in-place update on all subnets".
- **Test the module** - `terraform plan` against example configurations in CI, and Terratest or `terraform test` for anything critical (Q179).
- **Roll out by cohort** with automated bump PRs, never by re-pointing a tag.

### Q171. Workspaces versus directory-per-environment

**Workspaces** keep one configuration and one backend, with a separate state per workspace, selected by `terraform workspace select`.

**Directory per environment** keeps a directory (or repository) per environment, each with its own backend configuration and its own variable files, usually calling shared modules.

**For production isolation I use directory-per-environment**, for four reasons:

1. **Blast radius via the backend.** Separate directories mean separate backends, which can be in **separate cloud accounts** with separate credentials. Workspaces share one backend and one set of credentials, so an operator who can touch dev state can touch prod state, and a misconfigured backend affects all of them.
2. **`terraform workspace select` is a mode you can forget.** The single most dangerous property is that the same command in the same directory does different things depending on invisible state. Applying to prod because you did not switch back is a real and recurring incident. A directory is visible in the path, in the PR diff, and in the CI job name.
3. **Environments legitimately differ.** Production has resources non-production does not - a WAF, cross-region replication, a bigger topology, different providers. Expressing that in one configuration means `count = terraform.workspace == "prod" ? 1 : 0` scattered through the code, which is both ugly and untestable. Separate directories express it directly.
4. **Different change cadence and permissions.** CODEOWNERS on the prod directory, different required approvers, different CI workflows. Impossible to express on a workspace.

**Where workspaces are right**: ephemeral, identical environments from one configuration - a per-pull-request environment, a per-developer sandbox, per-tenant infrastructure that is genuinely identical. That is what they were designed for and they are good at it.

### Q172. Data sources versus remote state outputs

**Remote state output** (`terraform_remote_state`): read another state file's outputs directly.

- **Coupling created**: to the *other configuration's state file and its output names*. You need read access to that backend, you are bound to its implementation, and a change to an output name breaks consumers. It also reads the whole state, which for a state containing secrets means the consumer can read them.

**Data source** (`data "aws_vpc" "main" { tags = { Name = "prod" } }`): query the provider's API for the real resource.

- **Coupling created**: to the *real-world naming or tagging convention*. Loose, and it works across tools - the VPC could have been created by CloudFormation or by hand. But the lookup can fail or return the wrong thing if the convention drifts, and it is resolved at plan time so it adds API calls.

**The alternative I prefer for cross-stack references**: an explicit **contract in a neutral store** - publish the values one layer produces into **SSM Parameter Store** (or Secrets Manager) under a documented, versioned path, and have consumers read those parameters via a data source.

```hcl
resource "aws_ssm_parameter" "vpc_id" {
  name  = "/platform/${var.env}/vpc_id"
  value = aws_vpc.main.id
}
# consumer
data "aws_ssm_parameter" "vpc_id" { name = "/platform/${var.env}/vpc_id" }
```

Why this is better: the contract is **explicit and named**, so it is obvious what is public; the consumer needs no access to the producer's state; it works for consumers that are not Terraform; and the coupling is to a documented parameter path rather than to another team's internal structure. The cost is one more moving part and a small amount of ceremony.

Ranked: parameter-store contract > data source by tag > remote state. Remote state is the easiest and the one that creates the most coupling, which is the usual shape of these things.

### Q173. Reviewing a plan in CI

**The flow:**

1. On a pull request, CI runs `terraform init`, `validate`, `fmt -check`, then **`terraform plan -out=tfplan`**.
2. It converts the plan to JSON (`terraform show -json tfplan`) and runs **policy checks** (Q175) against it.
3. It posts a **human-readable summary** as a PR comment: the counts of add/change/destroy, and the full plan output (collapsed). The counts matter more than the text - a reviewer reliably notices "3 to destroy" and reliably does not read 900 lines.
4. The **binary plan file is stored as an artifact**, keyed to the commit and the PR.
5. On merge, the apply job **uses that saved plan file** rather than re-planning.

**Where the plan is stored**: as a CI artifact or in a bucket, with a short retention. It matters that it is the *binary* plan, not the text, because that is what `terraform apply tfplan` consumes. It also matters that **the plan can contain secrets** - resource attributes are in there in cleartext - so the artifact must be access-controlled and the PR comment must not include sensitive values (`-no-color` output of a plan will happily print an unmarked password).

**What makes an apply diverge from the reviewed plan:**

- **Time.** The plan was made against the world as it was; anything changed since - a manual console edit, another team's apply, a resource deleted - and applying a saved plan **fails** rather than diverging, because Terraform records the state serial in the plan and refuses if it moved. That refusal is the safety property, and it is why saved plans are correct.
- **Applying without the saved plan.** If the apply job runs a fresh `terraform plan && apply -auto-approve`, everything above is void - you reviewed one plan and applied another. This is the most common real divergence and it is entirely self-inflicted.
- **`-target` or changed variables** between plan and apply.
- **Provider version drift** if versions are not locked (Q174) - a re-init pulling a new provider can produce a different plan.
- **Values unknown at plan time** ("known after apply"). A plan containing computed values that feed into other resources can produce apply-time behaviour the plan could not show. This is inherent, and it is why a plan is a strong signal rather than a guarantee.
- **Partial failure** mid-apply (Q176).

### Q174. Provider pinning and the lock file

**Two separate things:**

- **`required_providers` version constraints** in configuration (`version = "~> 5.0"`) declare the acceptable range.
- **`.terraform.lock.hcl`** records the **exact version selected and the checksums of the provider binaries** for each platform. It is generated by `terraform init` and **must be committed**.

The lock file is what makes provider resolution reproducible: `terraform init` uses the locked version if it satisfies the constraints, rather than re-resolving to the newest match. `terraform init -upgrade` is the deliberate act of moving it.

**What breaks in six months without pinning:**

1. **A provider major version lands** with breaking schema changes - a renamed attribute, a removed resource type, a changed default. Your configuration no longer validates, or worse, validates and plans a replacement.
2. **A changed default silently rewrites resources.** The AWS provider changing a default value (an encryption setting, a tag behaviour, a lifecycle default) turns a no-op plan into an in-place update - or a destroy-and-create - across hundreds of resources. This is the failure that costs an outage.
3. **The plan differs by operator.** Your laptop has 5.20, CI has 5.44, a colleague has 5.31. Three different plans from the same configuration, which makes review meaningless.
4. **Supply chain exposure.** Without checksums in the lock file, a compromised or substituted provider binary is undetectable. The lock file's `h1:` hashes are a real security control.
5. **Terraform's own version.** Same problem, solved separately with `required_version` and a pinned version in CI and in `.terraform-version`.

**The policy**: pin the provider to a minor range (`~> 5.44`), commit the lock file, include all platforms you build on (`terraform providers lock -platform=linux_amd64 -platform=darwin_arm64`), and upgrade deliberately via a PR whose plan you read - which is exactly the automated-dependency-update flow of Q57, applied to infrastructure.

### Q175. Policy as code

| Tool | Model |
| --- | --- |
| **OPA / Conftest (Rego)** | General policy engine; evaluate Rego rules against the **plan JSON**. Open source, works on anything JSON, but Rego is a real learning curve. |
| **Sentinel** | HashiCorp's policy language, integrated into Terraform Cloud/Enterprise with enforcement levels (advisory / soft-mandatory / hard-mandatory). Better integrated, commercial. |
| **Checkov / tfsec / Terrascan** | Rule libraries with hundreds of built-in security checks, run against **HCL source** or plan JSON. Zero-effort baseline coverage; less good for organization-specific policy. |

**Where the check belongs**: **on the plan JSON, in the pull request, before apply.** Two reasons: the plan resolves variables, modules and computed values, so it reflects what will actually exist - a source-level scan of HCL cannot see what a module produces; and it is the last point where the change is cheap to stop.

Layered:

1. **Pre-commit / editor**: `fmt`, `validate`, fast Checkov rules. Advisory.
2. **Pull request, blocking**: policy against the plan JSON - encryption required, no public S3, no `0.0.0.0/0` ingress on sensitive ports, mandatory tags, approved instance families, no resource destroys without a label.
3. **Runtime, as a second line**: AWS Config rules or a cloud security posture tool, catching what was created outside Terraform.

**Existing violations** are the question that separates a workable rollout from a failed one:

1. **Run in advisory mode first** and publish the inventory. You will find hundreds.
2. **Fail only on *new* violations** - compare the plan's introduced violations against a recorded baseline. This is the key move: the policy blocks regression immediately while remediation proceeds on its own schedule.
3. **Explicit, expiring exceptions.** An exception file with an owner, a reason and a date; expired exceptions fail the build. Not a permanently suppressed rule.
4. **Burn down the baseline** on a plan with dates, prioritized by severity, and make it visible.
5. **Ratchet**: the baseline count may only decrease, enforced by CI.

Turning on a hard-fail policy against an estate with 400 existing violations gets the policy disabled within a fortnight. Grandfathering plus a ratchet gets it adopted.

### Q176. Apply timed out mid-way `[T]`

**The state of the world:**

- Terraform applies the dependency graph in parallel, resource by resource, and **writes state after each resource completes**. So state reflects everything that finished.
- Resources created **before** the timeout: real, and recorded in state. Fine.
- The resource **in flight** when the process died: this is the dangerous case. It may exist in the cloud but **not be recorded in state** - an orphan. The API call succeeded; Terraform died before persisting.
- Resources **after** it: not created.
- Some resources may be marked **tainted** in state if the provider reported a partial creation failure before the timeout.
- The **state lock is still held**, because the process did not release it (Q165).

**Recovery procedure:**

1. **Confirm the process is really dead** - the CI job, the local process, any retry. Do not proceed while an apply might still be running.
2. **`terraform force-unlock <ID>`** using the ID from the error.
3. **Verify the state is the latest version.** S3 versioning means you can compare; check the serial number is what you expect and that state was not corrupted by a partial write.
4. **`terraform plan`** and read it very carefully. This is the diagnostic step. What it shows tells you what happened:
   - Resources it proposes to **create that you believe already exist** → orphans. Verify in the console/API, then **`terraform import`** each one, or delete them manually if they are safe to delete and let Terraform recreate. Import is safer for anything stateful.
   - Resources marked **tainted** → they will be replaced; decide whether that is acceptable.
   - Otherwise a clean plan of the remaining work → just apply.
5. **Reconcile orphans deliberately**, one at a time, re-planning after each import until the plan matches your intent.
6. **Then apply.**

**Prevention**: CI apply jobs with a timeout longer than any realistic apply, signal trapping so the lock is released on cancellation, `-lock-timeout` set, smaller states so applies are short (Q167), and never running apply from a laptop for production.

### Q177. Terraform, CloudFormation, Pulumi, Crossplane

What **genuinely** distinguishes them, beyond language:

- **Where the state lives.** Terraform: a state file *you* own and must protect (Q164). CloudFormation: AWS owns and manages it - no state file to lose, corrupt or lock, and automatic rollback of a failed stack update. Pulumi: a state file, in their service or your backend, same model as Terraform. Crossplane: **state is the Kubernetes API and etcd** - resources are custom resources, reconciled continuously.
- **Push versus continuous reconciliation.** Terraform, CloudFormation and Pulumi are **run-based**: they converge when you run them, and drift persists until the next run. **Crossplane is a controller**: it reconciles continuously, like the rest of Kubernetes, so drift is corrected automatically. That is a categorical difference, not a stylistic one.
- **Multi-provider scope.** Terraform and Pulumi manage anything with a provider - AWS, Kubernetes, Datadog, GitHub, PagerDuty - in one graph. CloudFormation is AWS-only (with third-party resource types as a limited escape). This matters more than people expect: managing a DNS record, a monitor and a cloud resource in one change is common.
- **Programming model.** Pulumi uses general-purpose languages, which buys you real abstraction, types and testing - and costs you the property that the configuration is *inspectable without executing it*. Terraform's HCL is deliberately limited so that a human and a policy engine can read it. This is a genuine trade-off, not a preference.
- **The plan.** Terraform and Pulumi produce a reviewable diff before acting; CloudFormation change sets do too but are less legible; Crossplane has no plan at all, which is its main operational weakness.
- **Ecosystem and provider coverage lag.** Terraform's AWS provider usually supports new services faster than CloudFormation, historically.

**How I choose**: Terraform for a multi-cloud or multi-SaaS estate and as the default; CloudFormation/CDK when the organization is AWS-only, wants no state to manage, and values Service Catalog and AWS-native integration; Pulumi when the team is strong and the abstraction genuinely pays; Crossplane when you want application teams to request infrastructure through the Kubernetes API as part of a platform (Q265) - which is a platform-design decision more than an IaC one.

### Q178. Terraform's Kubernetes provider versus GitOps

**The line I draw:** Terraform provisions **the cluster and everything the cluster cannot provision for itself**; GitOps manages **everything inside the cluster**.

Concretely:

| Terraform | GitOps (Argo CD / Flux) |
| --- | --- |
| The EKS cluster, node groups, IAM roles and IRSA trust policies, VPC, security groups | Every application Deployment, Service, Ingress, ConfigMap |
| Cloud resources the workloads depend on: RDS, S3, SQS, ElastiCache | Platform components: ingress controller, cert-manager, external-secrets, monitoring stack |
| The **bootstrap**: install Argo CD itself, and the root Application pointing at the GitOps repository | Everything Argo CD then manages, including its own configuration |

**Why not use Terraform for in-cluster resources**, beyond bootstrap:

- **Terraform is run-based; Kubernetes is reconciliation-based.** Managing a Deployment in Terraform means drift persists until someone runs Terraform, and the two models fight over ownership of fields (the HPA problem of Q155, but worse because Terraform has no `ignoreDifferences` equivalent that is as granular).
- **Terraform's Kubernetes provider needs cluster credentials at plan time**, which means CI holds them - giving back the security property of Q150.
- **The plan is unreliable** for resources whose schema comes from a CRD that does not exist yet, producing the classic chicken-and-egg failure where a single apply cannot both install a CRD and create a custom resource.
- **Deployment velocity mismatch.** Application manifests change many times a day; Terraform's review-plan-apply cycle is built for infrequent, high-consequence changes.

**Why not use GitOps for cloud resources**: you can (Crossplane, ACK, the Terraform operators), and it is a legitimate platform pattern - but it makes the cluster a dependency of your cloud infrastructure, which inverts the failure hierarchy. If the cluster is gone, you want to be able to rebuild it, and that requires the cloud layer to be managed by something outside it.

**The bootstrap seam** is the interesting part: Terraform creates the cluster and installs Argo CD (via the Helm provider) with a single root Application - the "app of apps" - and then stops. Everything after that is git. That gives one clean handover point rather than a blurred boundary.

### Q179. Testing infrastructure code

**What is actually testable, in increasing cost:**

1. **Static**: `fmt`, `validate`, linting (TFLint), security rules (Checkov). Catches syntax, deprecated usage, obviously wrong configuration. Seconds, and it should be on every commit.
2. **Plan-time assertions**: render a plan for an example configuration and assert on the plan JSON - "this module produces exactly 4 subnets", "encryption is enabled", "no resource is destroyed", "the instance type is from the approved list". Terraform's native `terraform test` framework (1.6+) with `command = plan` does this, as does Conftest against plan JSON. Fast, no cloud resources, no cost.
3. **Apply-time / integration**: actually create the resources in a sandbox account, assert on the real world (the endpoint responds, the IAM policy permits what it should and denies what it should not), then destroy. Terratest, or `terraform test` with `command = apply`. Minutes to tens of minutes, real money, and flaky in the way all integration tests are.
4. **Contract on the module interface**: assert that outputs exist and have the right shape, so a consumer's build breaks at module-upgrade time rather than at apply time.

**What plan-time catches that apply-time does not**: nothing, in terms of *correctness* - but it catches things **cheaply enough to run on every PR**, which is the entire point, and it catches the one thing that matters most, which is **an unintended destroy or replacement**. A plan test asserting "this change produces zero replacements" is the single highest-value infrastructure test there is, because resource replacement is the mechanism behind most Terraform-caused outages (Q169, Q174).

**What apply-time catches that plan-time cannot**: whether the resources actually work together - IAM permissions that are syntactically valid and functionally wrong, security group rules that do not permit the traffic you think, a module whose outputs are correct and whose resources cannot reach each other. Also anything with "known after apply" values, which the plan cannot evaluate.

**My practical position**: static and plan tests on every PR for everything; apply tests in a sandbox for **shared modules only**, on release, because that is where the blast radius justifies the cost. Testing every environment's root configuration with apply tests is rarely worth it - a `plan` against the real environment is a better signal and it is free.

### Q180. 4,000 lines in one root module `[A]`

The three problems in order of danger: **applies from laptops** (unaudited, unreviewed, unlockable in practice), **no tests** (every change is a gamble), and **one root module** (a 30-minute plan nobody reads, and a total blast radius).

**Days 1-15 - stop the bleeding, change nothing structural.**

1. **Move state to a remote backend with locking** if it is not already, with S3 versioning and encryption. If state is on someone's laptop, this is the emergency.
2. **Back up state**, and verify you can restore it. Everything that follows risks state.
3. **Pin the Terraform version and all providers, commit the lock file** (Q174). Half the "mysterious plan" problems disappear here.
4. **Get a clean plan.** Run a plan and understand every diff. If the plan is not empty, the code does not describe reality and nothing else is trustworthy. Resolve each item - adopt, revert, or `ignore_changes` - until it is a no-op.
5. **Read-only in the console for production**, or at least alerting on console writes.

**Days 15-45 - make change safe.**

6. **CI pipeline**: plan on PR with the output posted as a comment, apply on merge from the saved plan file, using OIDC federation rather than a stored key (Q234). **Remove laptop apply access to production.** This is the single biggest risk reduction in the whole exercise.
7. **A CI check that fails any plan containing a destroy or replacement** without an explicit label. Cheap, and it prevents the Q169 class of incident immediately.
8. **Static checks and a policy baseline in advisory mode** (Q175), with the violation inventory published and a ratchet so it cannot grow.
9. **`fmt`, `validate`, TFLint** as required checks.

**Days 45-90 - split and extract, carefully.**

10. **Split state by layer** (Q167), starting with the *least* coupled slice - usually application-level resources - and moving it out with `terraform state mv` or `moved` blocks, one slice at a time, verifying a no-op plan after each. Never split everything at once.
11. **Extract the obvious repeated patterns into versioned modules**, but only where the repetition is real. Premature modularization of a codebase you do not yet understand is how you get 4,000 lines in three repositories.
12. **Add plan-time tests** for the extracted modules (Q179).
13. **Document the layering and the apply order**, because splitting state creates an ordering obligation that did not exist before.

**What I would not do**: rewrite it. A greenfield rewrite of working infrastructure has an enormous downside and almost no upside - the risk is entirely in the transition, and the existing code, however ugly, describes something that currently works. Improve it in place, under test, with the pipeline in front of it.

**How I would sequence the conversation with the team**: the first two weeks produce no visible change and remove the ability to apply from a laptop, which will be unpopular. Framing it as "we are making it possible to change this safely" rather than "your code is bad" matters, and shipping the CI pipeline early gives them something faster and better rather than only a restriction.

*Hook: an infrastructure codebase you inherited, and the first change you made.*

---

## 12. Observability - metrics, logs, traces and SLOs

### Q181. Monitoring versus observability

**Monitoring** is watching a predefined set of signals for predefined conditions. You decide in advance what could go wrong, instrument for it, and alert when it does. It answers **known questions**.

**Observability** is the property that you can determine the internal state of the system from its external outputs, **including for questions you did not anticipate**. The operational test is: when something breaks in a way nobody predicted, can you find out why *without shipping new code*?

The useful framing rather than the slogan: monitoring optimizes for **known failure modes** and is about **detection**; observability optimizes for **unknown failure modes** and is about **explanation**. You need both. A system with excellent observability and no monitoring nobody notices is broken; a system with excellent monitoring and no observability tells you it is broken and cannot tell you why.

The practical consequence for how you instrument: monitoring pushes you toward a small number of low-cardinality aggregate signals with alerts on them. Observability pushes you toward **high-cardinality, high-dimensional data** you can slice arbitrarily after the fact - which is exactly what metrics cannot do (Q183) and what traces and structured events can. That tension is the whole design problem of Q200.

### Q182. The signals, and which to reach for

| Signal | Best at |
| --- | --- |
| **Metrics** | "Is something wrong, how much, and since when?" Cheap, aggregated, long retention, good for alerting and trends. Cannot tell you about one request. |
| **Logs** | "What exactly happened in this code path?" Highest detail, arbitrary structure, expensive at volume. Bad at aggregate questions. |
| **Traces** | "Where did the time go, across services?" The only signal that shows causal structure across process boundaries. |
| **Profiles** | "Where did the time go, inside one process?" CPU, allocation, lock contention at the line level. |
| **Events / change records** | "What did we change?" Deployments, flag flips, config changes, scaling events. The most under-used signal, and the answer to a large share of incidents. |

**For a latency incident**, in order:

1. **Metrics** - confirm it is real, quantify it, establish when it started, and see which service and which endpoints. Compare against the SLO to decide urgency.
2. **Change events** - what deployed, what flag flipped, what config changed at that minute. This resolves a third of incidents before any deeper analysis.
3. **Metrics again, sliced** - is it all traffic or one endpoint, one tenant, one AZ, one pod, one node? Narrowing the domain is worth more than any tool.
4. **Traces** - take an exemplar from the slow bucket (Q197) and look at the span breakdown. This tells you *which hop* is slow, which is the question metrics cannot answer.
5. **Logs** for that trace ID - the detail of what happened in the slow span.
6. **Profiles** if the slow span is CPU or allocation inside one service with no downstream explanation.

The wrong tool for "why is this one request slow" is **metrics**, because aggregation has already destroyed the individual request. That is the whole reason traces exist.

### Q183. The Prometheus data model and cardinality

A **time series** is uniquely identified by its **metric name plus the full set of label key-value pairs**. `http_requests_total{method="GET", path="/orders", status="200", instance="10.1.2.3:8080"}` is one series; changing any label value creates a different one. Each series holds a sequence of (timestamp, float64) **samples**.

**Cardinality is the number of distinct series**, and it is the product of the distinct values of every label. Four labels with 10, 5, 20 and 100 values is 100,000 series from one metric name.

**What it costs:**

- **Memory, and this is the binding constraint.** Prometheus holds an in-memory index and, for every *active* series, a head chunk being written. The rule of thumb is roughly **2-4 KB of resident memory per active series**, so a million series is 2-4 GB before you have run a query. The inverted index mapping label pairs to series IDs is also memory-resident and grows with distinct label *values*.
- **Ingestion CPU**, proportional to series count per scrape, since each sample must be looked up in the index.
- **Query time and query memory.** A query's cost is proportional to the number of series it touches, not the number it returns. `sum(rate(http_requests_total[5m]))` over a million series must decompress and rate a million series before summing one number. Queries are the thing that actually OOMs a Prometheus.
- **Disk**, but this is the cheap one - compression is excellent (1-2 bytes per sample) and it is not usually the limit.

The number that matters operationally: **`prometheus_tsdb_head_series`**, watched as a trend, with an alert on the rate of increase. Absolute size matters less than the shape of the curve, because a cardinality incident is always a sudden inflection.

### Q184. Someone adds a user_id label `[T]`

Over the next hour:

1. **Minute 0-1**: the new build deploys. Each pod's `/metrics` endpoint begins exposing one series per metric per user seen by that pod. The exposition payload grows from kilobytes to megabytes.
2. **First scrape**: Prometheus ingests them. `prometheus_tsdb_head_series` jumps. Every series is new, so every one requires an index insert and a new head chunk allocation.
3. **Minutes 1-15**: memory climbs steeply and roughly linearly with unique users seen. With 100,000 daily active users and 20 instrumented metrics, that is 2 million new series, so **4-8 GB** of additional resident memory. Scrape duration rises as the exposition payload grows, and if it exceeds the scrape timeout the target starts failing scrapes - so you begin **losing data for that job entirely**, including the metrics you actually need.
4. **Minutes 15-30**: queries slow down badly. Every dashboard and every recording rule touching that metric now fans out over millions of series. Rule evaluation starts exceeding its interval, so **recording rules and alerting rules begin to be skipped** - which means alerts silently stop firing. This is the most dangerous part: the observability system fails quietly.
5. **Minutes 30-60**: Prometheus is OOMKilled. It restarts, replays the write-ahead log - which for a huge head block takes **minutes**, during which it is scraping nothing and evaluating nothing - and then OOMs again as the series return. A crash loop.
6. **Blast radius**: this is one Prometheus for many services. Everyone's alerting is now down, during whatever the original incident was.

**Recovery**: `metric_relabel_configs` with a `labeldrop` on `user_id` at scrape time is the fastest fix that does not require a deploy - it drops the label before ingestion, collapsing the series back. Then roll back the instrumentation. The head series do not disappear until they age out of the head block (two hours) plus retention, so memory recovers slowly.

**Prevention**: `sample_limit` and `label_limit`/`label_value_length_limit` on the scrape config, so a runaway target fails its own scrape instead of the server; an alert on head-series growth rate; and, if per-user analysis is genuinely needed, it belongs in traces, logs or a wide-event store, not in metrics (Q144 in `03-microservices`).

### Q185. Counter, gauge, histogram, summary

- **Counter** - monotonically increasing; only resets on restart. Always query it through `rate()` or `increase()`, never raw. Requests, errors, bytes, events.
- **Gauge** - a value that goes up and down. Queue depth, temperature, in-flight requests, memory used.
- **Histogram** - counts observations into cumulative buckets, plus `_sum` and `_count`. Bucket boundaries are fixed at instrumentation time. **Aggregatable across instances**, and quantiles are computed at query time.
- **Summary** - computes quantiles **client-side** over a sliding window, exposing them directly (`quantile="0.99"`), plus `_sum` and `_count`.

**When a summary is wrong**: almost always, in a distributed system - because **you cannot aggregate its quantiles**. A summary from each of 20 pods gives you 20 p99 values and no way to combine them into a service-level p99. You can average them, and the average of 20 p99s is not the p99 of the whole; it is a number with no meaning. Summaries also cannot be re-quantiled after the fact - if you instrumented p50/p90/p99 and now need p999, you must change the code and wait.

Summaries are appropriate only for a single-instance component where client-side accuracy matters and aggregation never will.

**Why you cannot average percentiles**: a percentile is a **rank statistic over a distribution**, not a mean. Consider two pods: pod A serves 1,000 requests with p99 = 10 ms; pod B serves 10 requests with p99 = 1,000 ms. The average of the p99s is 505 ms. The true p99 of the combined 1,010 requests is about 10 ms, because pod B's slow requests are far fewer than 1 percent of the total. The average is wrong by two orders of magnitude, and it is wrong in the *dangerous* direction in the reverse case - a small heavily-loaded pod's terrible tail is averaged away into invisibility.

The correct operation is to aggregate the **underlying distribution** (the bucket counts) and then compute the quantile: `histogram_quantile(0.99, sum by (le) (rate(http_duration_bucket[5m])))`. Note the `sum by (le)` **inside** - summing bucket counts first, quantile second. That ordering is the whole point, and getting it backwards is a common dashboard bug.

### Q186. Histogram buckets and quantile error

**Choosing buckets**: they must be chosen at instrumentation time and they should straddle the values you care about, with resolution concentrated where decisions are made.

- Start from the **SLO threshold**. If your SLO is "99 percent of requests under 300 ms", you need a bucket boundary *exactly* at 0.3, because that is the only boundary that gives an exact answer. This is the most important rule: put a boundary at every threshold you will ever assert on.
- Use a **roughly exponential** spread across the plausible range: `.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10` (Prometheus's default) covers a typical HTTP service. Adjust the range to your service - defaults are wrong for a 5 ms cache and for a 60 s batch call.
- Keep the count modest: **10-15 buckets**. Each bucket is a series, multiplied by every other label, so buckets are a cardinality multiplier.
- Always have a `+Inf` bucket (implicit) and make sure the top finite bucket is above your timeout, or everything slow collapses into `+Inf` and is unmeasurable.

**What `histogram_quantile` computes**: it finds the bucket containing the target rank, then **linearly interpolates within that bucket** assuming observations are uniformly distributed across it. It is an estimate, not a measurement.

**The error** is therefore bounded by the bucket width containing the quantile, and it can be large. If p99 falls in the bucket `[1, 2.5]`, the reported value is somewhere in that range with up to 1.5 seconds of error, and the interpolation assumption (uniform distribution) is systematically wrong for latency, which is heavily skewed toward the lower edge - so interpolation typically **overestimates**. Two further failure modes: a quantile falling in the `+Inf` bucket returns `+Inf` (interpolation is impossible with no upper bound), and a bucket with very few observations gives a noisy, meaningless answer.

**Native histograms** (Prometheus 2.40+, stable-ish and the direction of travel) change this fundamentally: instead of user-chosen buckets, they use **automatically-generated exponential buckets** with a configurable resolution, stored as a single series rather than one series per bucket. The consequences: cardinality drops by roughly the bucket count (10-15×), resolution is far higher and uniform across the range, you no longer have to guess boundaries in advance, and buckets can be re-resolved at query time. The costs are that the storage format is different (so remote-write targets and Grafana need support), and that the exponential scheme still cannot place a boundary exactly on your SLO threshold.

### Q187. Pull versus push

**Pull**: the server scrapes an endpoint on each target on a schedule. **Push**: the target sends samples to the server.

**What pull gives you operationally:**

1. **Target liveness for free.** A failed scrape is itself a signal - `up == 0` - so you detect a dead or unreachable instance without the instance having to report anything. In a push model, silence is ambiguous: is it down, or is it fine and idle?
2. **The monitoring system controls its own load.** The server decides the scrape interval and can back off; it cannot be overwhelmed by a target that decides to send a million samples a second. Push systems need rate limiting and back-pressure that they usually do not have.
3. **Service discovery is the configuration.** Prometheus discovers targets from Kubernetes, EC2, Consul, and knows what *should* exist. That is how it can tell you something is missing, which a push system fundamentally cannot.
4. **Trivially debuggable.** `curl localhost:8080/metrics` shows you exactly what the server will see. No agent, no pipeline, no wondering where the data went.
5. **No configuration in the target.** The application does not know or care where its metrics go, so redirecting, duplicating or adding a monitoring environment is a server-side change.

**Short-lived jobs** break the model, because the process may not exist when the scrape comes. Options:

- **Pushgateway**, for the specific case of a batch job whose result should persist: the job pushes on completion, Prometheus scrapes the gateway. The important caveats: it is **not** a general push mechanism, it holds values forever until deleted (so a job that stops running keeps reporting its last value - a stale-data trap), and it breaks the liveness property. Use it only for genuine batch outcomes (`last_success_timestamp`), and alert on staleness of that timestamp.
- **Better: make the job's outcome a state, not an event.** A CronJob writes its result somewhere durable and a long-lived exporter exposes it. This restores every property of pull.

**Serverless and very short-lived functions** are where pull genuinely does not fit, and the honest answer is that you use a push path - the **OpenTelemetry Collector with an OTLP receiver and a Prometheus remote-write exporter**, or the vendor's agent. This is also why remote-write-first systems (Mimir, Thanos Receive, Grafana Cloud) exist and are increasingly common: at that point Prometheus's pull model is preserved where it works and bypassed where it does not.

### Q188. Prometheus at scale

The order in which you hit the problems, and what solves each:

1. **First limit: a single Prometheus runs out of memory or disk.** Solved by scaling *up* first (it goes a long way - a single server handles millions of series) and by reducing cardinality.
2. **Second limit: you need longer retention than local disk allows.** Prometheus's local TSDB is designed for weeks, not years, and is not replicated.
3. **Third limit: you need a global view across many Prometheus servers** - per-cluster, per-region, per-team.
4. **Fourth limit: high availability** - a single Prometheus is a single point of failure, and running two identical ones gives you duplicate, slightly-offset data.

| | Solves | How |
| --- | --- | --- |
| **Federation** | A limited global view | A central Prometheus scrapes *aggregated* series from others. Only works for pre-aggregated, low-cardinality data - federating raw series just moves the scaling problem. Largely superseded. |
| **Remote write** | Getting data out of Prometheus into something durable | Prometheus streams samples to a remote endpoint as it ingests. The foundation for everything below. |
| **Thanos** | Long retention, global query, HA, deduplication | A **sidecar** next to each Prometheus uploads completed TSDB blocks to object storage; a **Querier** fans out over sidecars and a **Store Gateway** to answer queries across all of them, deduplicating HA pairs; a **Compactor** compacts and downsamples blocks in object storage. Prometheus stays the ingestion point. |
| **Mimir** (and Cortex) | The same, as a horizontally scalable multi-tenant service | Prometheus **remote-writes** into a distributed cluster: distributors shard by series to ingesters, ingesters write blocks to object storage, queriers fan out. Multi-tenant with per-tenant limits. Prometheus becomes a scraper and forwarder. |

**Thanos versus Mimir** in one line: Thanos keeps Prometheus as the system of record and federates over it (simpler to adopt incrementally, sidecar model); Mimir treats Prometheus as an agent and centralizes ingestion (better multi-tenancy, per-tenant limits and horizontal scaling, but a bigger system to run). For an estate with many clusters and one platform team, I would run Mimir (or a vendor equivalent) and use **Prometheus in agent mode** for scraping. For a smaller estate wanting long retention without a distributed system, Thanos sidecars plus object storage is a much smaller step.

### Q189. Recording rules and query cost

A recording rule evaluates a query on a schedule and stores the result as a new series. You materialize a query when:

- It is **expensive and repeated** - on several dashboards, or in alerting rules that run every 15 seconds.
- It **aggregates away high cardinality** - `sum by (service, status) (rate(http_requests_total[5m]))` collapses thousands of per-pod series into a handful. This is the highest-value case, because the expensive part is the fan-out, and doing it once per interval rather than once per dashboard load is a large saving.
- It is used by **long-range queries**. A 30-day graph over raw series is brutal; over a pre-aggregated series it is cheap.
- It **standardizes a definition** - one recording rule for "error ratio" means every dashboard and alert uses the same arithmetic. This is a correctness benefit as much as a performance one, and it is how multi-window burn-rate alerting (Q204) is made maintainable.

Naming convention: `level:metric:operations`, e.g. `service:http_requests:rate5m`.

**The trap with recording rules over a rate**: you must **record the rate, not re-rate the recording**, and you must never take a rate of a recorded rate. Concretely:

- Recording `job:http_requests:rate5m = sum by (job) (rate(http_requests_total[5m]))` is correct: rate first (per-series, handling counter resets correctly), then sum.
- Recording `sum by (job) (http_requests_total)` and then applying `rate()` to it later is **wrong**: summing counters across instances produces a series that drops whenever any instance restarts, and `rate()` interprets that drop as a counter reset, silently losing data. This is the classic bug.
- Equally, you cannot meaningfully take a longer rate of a recorded 5-minute rate. To support multiple windows you record each window separately, or record the counter aggregation carefully with `sum(rate(...))` per window.
- The other trap: **the recorded series inherits the evaluation interval as its resolution**, so a rule evaluated every minute cannot answer questions at finer granularity, and a `[5m]` window recorded every minute is smoothed. That is usually fine, but it means recording rules are not a lossless substitute for the raw data.

### Q190. rate() over a reset, and a short window `[T]`

**Counter reset**: `rate()` and `increase()` explicitly handle resets. Prometheus iterates the samples in the window, and whenever a sample is **lower than the previous one**, it assumes the counter reset to zero and adds the previous value as the increment before continuing. So a counter going 100 → 110 → 5 → 15 in a window is treated as increasing by 10, then by 5 (reset, so 5 counts from zero), then by 10 - total 25, extrapolated over the window. The result is correct as long as the counter did not reset *and then exceed its previous value within one scrape interval*, which would be undetectable.

The important corollary: this only works on a **single series**. Summing counters across instances before rating (Q189) destroys it, because one pod restarting makes the sum dip and `rate()` treats it as a reset of the whole aggregate.

`rate()` also **extrapolates** to the window edges - if the first and last samples do not sit exactly at the window boundaries, it scales the observed increase to cover the full window, which is why `increase()` over a short window on a slow counter can return non-integer values like 2.7 events.

**Window shorter than the scrape interval**: `rate()` needs **at least two samples** in the window to compute a difference. With a 30-second scrape interval and `rate(x[15s])`, most evaluations see zero or one sample, so the result is **empty** - no data point, not zero. The graph shows gaps or nothing at all, and an alerting rule on it silently never fires, which is the dangerous outcome. (Prometheus 3 relaxes some of this, but the principle holds.)

The rule: **the range must be at least 4× the scrape interval**, and 5-10× is the safe default. With a 30-second scrape, use `[2m]` or `[5m]`, never `[1m]`. This is also why a service's scrape interval and its alerting windows have to be designed together, and why copying an alert rule between environments with different scrape intervals produces an alert that quietly does nothing.

### Q191. Structured logging

**Mandatory fields on every line:**

| Field | Why |
| --- | --- |
| `timestamp` | ISO-8601 with timezone and millisecond precision |
| `level` | For filtering and routing |
| `service`, `version`, `instance` | Which code, where. `version` is what lets you correlate a log change to a deployment |
| `environment` | So a staging log never gets mistaken for production |
| `trace_id`, `span_id` | The single most valuable field - it is what joins logs to traces (Q195) |
| `message` | Human-readable, and **static** - variable parts go in fields, so lines are groupable |
| `logger` / `source` | Where in the code |
| Error fields: `error.type`, `error.message`, `error.stack` | Structured, not concatenated into the message |
| Request context where applicable: `http.method`, `http.route` (the **template**, not the resolved path), `http.status_code`, `duration_ms` | |

Use the **OpenTelemetry semantic conventions** for these names rather than inventing your own - it means every tool understands your logs and you can correlate across services that were instrumented by different teams.

**What should never be logged:**

- **Credentials of any kind** - passwords, tokens, API keys, session identifiers, private keys. Including in a stack trace, a request dump, or an exception's message.
- **PII beyond what is necessary and lawful** - names, emails, addresses, phone numbers, national identifiers, dates of birth. Where an identifier is needed, log a pseudonymous or hashed one.
- **Payment data** - card numbers, CVV. PCI-relevant and non-negotiable.
- **Health, biometric or other special-category data.**
- **Full request or response bodies** by default. They contain all of the above and they are the single largest volume driver.
- **Anything with unbounded cardinality in a field you will index**, which is a cost problem rather than a compliance one.

The enforcement is not a policy document: it is a **serializer-level redaction filter** with an allow-list for known-safe fields, plus a detector in the log pipeline that alerts on patterns resembling secrets or card numbers. Relying on developers to remember is how you end up in Q126.

### Q192. Log levels, sampling and cost

**Levels in production**: `INFO` as the default, `WARN` and `ERROR` always on. `DEBUG` off. The discipline that matters is what *belongs* at each level - `INFO` should be state changes and significant events, not per-request narration. Most log cost is `INFO` lines that should never have been written.

**The cost curve** is the thing to be clear-eyed about: log cost is roughly linear in volume for ingestion and storage, but the *value* of a log line falls off a cliff with age and with duplication. The ten-thousandth identical line adds nothing. So the economics favour **aggressive sampling of the repetitive and full fidelity for the rare** - which is the opposite of a uniform sampling rate.

**Sampling strategies**, in order of usefulness:

- **Never sample errors.** They are rare and they are the reason you have logs.
- **Sample high-volume `INFO` deterministically by trace ID**, so a sampled request has *all* its lines across every service or none - a partially-sampled trace is worse than no trace.
- **Rate-limit per log statement** (log-once-per-N, or a token bucket per call site). This kills the pathological case where one broken loop produces 90 percent of your volume, without touching anything else.
- **Tail sampling of logs alongside traces**: keep everything for requests that were slow or errored, sample the successful ones hard (Q196).

**Debug detail for one request without global debug** - the actual question:

1. **Trace-based**: the request is already sampled at 100 percent for a subset of traffic, and the trace carries the detail. This is the modern answer - the detail lives in span attributes and events rather than log lines.
2. **Conditional logging on a request attribute**: a debug header, a flag on the user or tenant, or a sampled-and-marked request causes the logger to emit at `DEBUG` **for that trace only**, propagated via baggage so every downstream service does the same. This is genuinely powerful and under-used.
3. **Dynamic log level per logger**, changed at runtime (`/actuator/loggers` in Spring Boot) - narrow by *class*, not by request, so it is a blunter tool but it needs no propagation. Useful during an incident; must be time-bounded so it is not left on.
4. **Never** turn on global `DEBUG` in production: it changes the system's performance profile, can leak sensitive data, and typically multiplies volume by 10-100×, which is both a cost incident and an ingestion-pipeline incident.

### Q193. A log pipeline dropping lines `[T]`

The reason nobody notices is that **absence of a log line is indistinguishable from the event not happening**. Logs have no sequence number, no expected rate, and no delivery acknowledgement that reaches the application. So the failure is silent by construction, and you only discover it during an incident when the line you need is missing - which is the worst possible time.

**What to instrument:**

1. **A synthetic canary log line at a known rate.** Every service emits a heartbeat log line every 30 seconds. A query counts them per service per minute and **alerts when the count is below the expected rate**. This is the only end-to-end check that covers the whole pipeline including the parts you do not own, and it is the single most valuable thing on this list.
2. **The agent's own drop counters.** Fluent Bit exposes `fluentbit_output_dropped_records_total`, `fluentbit_input_records_total` versus `fluentbit_output_proc_records_total`; Vector, Fluentd and the OTel Collector have equivalents (`otelcol_processor_dropped_log_records`). Scrape them and alert on any non-zero rate. Most estates run these agents and never scrape their metrics.
3. **Buffer and queue depth on the agent**, with an alert on sustained growth - the leading indicator before dropping starts.
4. **Backpressure and rejection at the ingestion endpoint** - 429s and 5xx from the log backend, and the backend's own rate-limit and quota metrics. Most managed log services drop silently once you exceed a plan limit, and expose it only as a billing-adjacent metric.
5. **Volume as a time series per service**, alerted on a sudden *drop* as well as a spike. A service whose log volume falls 80 percent has either been fixed or has stopped being observed, and you want to know which.
6. **Kubernetes-specific**: kubelet's log rotation. Container logs rotate at 10 MB by default with a small number of files retained; a service logging faster than the agent reads gets its logs rotated away before shipping, and **nothing anywhere reports this**. Watch the agent's read position lag against file rotation.
7. **Timestamp lag** - the difference between event time and ingestion time - as a histogram. Rising lag means the pipeline is falling behind, which precedes dropping.

The framing worth giving: the logging pipeline is a **production system with an SLO**, and it needs monitoring like any other. The reason it usually does not have any is that the thing you would monitor it with is often the same system.

### Q194. OpenTelemetry and the Collector

- **API** - the interfaces application and library code compile against (`Tracer`, `Meter`, `Logger`). Deliberately separated so that **libraries can instrument themselves** against the API with no dependency on an implementation, and with a no-op default if no SDK is present.
- **SDK** - the implementation: samplers, processors, batching, resource detection, exporters. Configured by the application owner.
- **Collector** - a standalone process (agent on the node, or a gateway cluster) that receives, processes and exports telemetry. Pipelines of receivers → processors → exporters.
- **Semantic conventions** - the standardized names and meanings for attributes (`http.request.method`, `service.name`, `db.system`). This is arguably the most valuable part of the project: it is what makes telemetry from two teams using two languages comparable, and what lets a backend build a dashboard without knowing anything about your service.

**What the Collector does that in-process cannot:**

1. **Tail-based sampling** (Q196). It requires seeing *all spans of a trace* before deciding, which a single process cannot do because it only sees its own spans.
2. **Decouple the application from the backend.** Changing vendors, adding a second destination, or redirecting telemetry becomes a Collector config change rather than a redeploy of 40 services. This alone usually justifies it.
3. **Buffering and retry across application restarts.** A pod that is being terminated cannot retry a failed export; a Collector with a persistent queue can.
4. **Centralized enrichment and redaction.** Adding cluster, region and team attributes, and stripping PII, in one place with one policy - rather than trusting 40 services to do it consistently.
5. **Aggregation and cost control at the edge**: converting spans to metrics (`spanmetrics`), dropping high-cardinality attributes, filtering health-check spans, sampling. Doing this before egress is where the cost savings are (Q200).
6. **Protocol translation** - receive Prometheus, Jaeger, Zipkin, Fluent Forward, StatsD and OTLP; export whatever the backend speaks. It is the adapter layer that lets a heterogeneous estate converge.
7. **Reduced application overhead and connection count** - the application sends to localhost with a short timeout, rather than maintaining TLS connections to a remote backend from every pod.

The standard topology is both: an **agent** Collector as a DaemonSet (fast local receipt, resource detection, node-level enrichment) forwarding to a **gateway** Collector deployment (tail sampling, aggregation, egress).

### Q195. Context propagation and where Java loses it

**The mechanism**: the active span's context lives in a **context object** that must travel with the logical unit of work. On the wire it is serialized into the **W3C `traceparent` header** (version, trace ID, span ID, flags) plus `tracestate`, and re-parsed on the other side.

- **HTTP**: the client instrumentation injects `traceparent` on the outgoing request; the server instrumentation extracts it and makes it the parent of the server span. Works transparently for instrumented clients (`RestTemplate`, `WebClient`, Apache HttpClient, the JDK client).
- **Messaging**: the context is injected into **message headers** (Kafka record headers, JMS properties, SQS message attributes). The consumer extracts it and creates a span **linked** to the producer's, often as a `link` rather than a parent because the relationship is asynchronous and may be one-to-many (`03-microservices` Q143).
- **Within a process**: the context is held in a **`ThreadLocal`** (`Context.current()`), which is why crossing a thread boundary is the whole problem.

**Where it gets lost in a Java service:**

1. **Thread pools.** Submitting a `Runnable` to an `ExecutorService` runs it on a thread with no context. This is the number one cause. Fixed by wrapping the executor (`Context.taskWrapping(executor)`, or Spring's `ContextPropagatingTaskDecorator`), which the OpenTelemetry Java agent does automatically for common pools - and does not for a pool you constructed yourself.
2. **`CompletableFuture` chains**, especially with `supplyAsync` on the common ForkJoinPool. Same cause.
3. **Reactive pipelines** (Reactor, WebFlux). There is no thread affinity at all, so `ThreadLocal` is meaningless; context must travel in the Reactor `Context`. Micrometer's `ContextPropagation` and `Hooks.enableAutomaticContextPropagation()` bridge it, and it is easy to get wrong.
4. **`@Async` and `@Scheduled`.** A scheduled job legitimately starts a new trace, but an `@Async` method should continue the caller's - and by default does not unless the executor is decorated.
5. **Kafka and JMS listeners** where the producer did not inject headers, or a framework that strips unknown headers.
6. **Manual thread creation** - `new Thread(...)`.
7. **Across a gateway or proxy that does not forward the header.** An old NGINX config, an API gateway with a header allow-list, or a load balancer stripping unknown headers silently breaks the chain at the edge.
8. **Between the trace and the logs**: the trace continues fine but the MDC was not populated, so `trace_id` is missing from log lines. Fixed by the logging instrumentation (`logging-mdc` in the OTel agent, or Micrometer Tracing's Slf4j bridge), and worth verifying because it is the join key for Q182.

### Q196. Head-based versus tail-based sampling

**Head-based**: the decision is made at the **root span**, before anything is known about the request, usually by hashing the trace ID against a probability. The decision is encoded in the `sampled` flag of `traceparent` and propagated, so every service in the trace makes the same decision. Cheap, stateless, and the overhead is bounded and predictable.

**Tail-based**: all spans are exported to a Collector, which **buffers complete traces** and then applies policies to decide what to keep - keep everything with an error, everything slower than 500 ms, everything from this tenant, and 1 percent of the rest.

**What tail-based buys you**: the ability to keep exactly the traces that are interesting. Head-based sampling at 1 percent means you keep 1 percent of errors, so the rare failure you need is almost certainly not there (`03-microservices` Q142). Tail-based keeps 100 percent of errors and slow requests while dropping the boring majority, which is a far better cost-to-value ratio.

**What it costs:**

- **All spans must be exported**, so you pay the full network and application overhead regardless of what you keep. The saving is in the backend, not at the edge.
- **State and memory in the Collector.** It must buffer every span of every in-flight trace for a decision window (typically 10-30 seconds), which is gigabytes at moderate volume.
- **All spans of a trace must reach the same Collector instance**, which requires **trace-ID-aware load balancing** in front of the tail-sampling gateway (the `loadbalancing` exporter in an agent tier routing by trace ID). This is the operational complexity people underestimate.
- **A decision deadline.** A trace that is still open when the window expires is decided on incomplete information, so very long traces are handled badly.
- **It is a stateful, scale-out service** you now operate.

**Where it runs**: in the **Collector gateway tier**, never in the application. The topology is agent Collectors → a load-balancing tier routing by trace ID → tail-sampling gateway Collectors → backend.

**The pragmatic middle** worth naming: head-based sampling at a rate high enough to be useful (5-20 percent) plus **always sampling errors** via a `ParentBased` sampler with local overrides, which captures most of the value with none of the infrastructure. Move to tail-based when volume makes that too expensive.

### Q197. Exemplars

An **exemplar** is a reference attached to a metric sample - specifically to a histogram bucket - recording a `trace_id` (and optionally a label set and timestamp) for one observation that landed in that bucket. So the p99 bucket on your latency histogram carries the trace ID of an actual slow request.

The value is that it closes the gap between "the aggregate says something is wrong" and "here is a specific example of it", which is normally the slowest step in an investigation. You click the spike on the latency graph and land in a trace of a request that caused it.

**What is required end to end:**

1. **Instrumentation that records exemplars.** Micrometer with a tracing bridge does this: when a timer observation is recorded inside an active span, it attaches the trace ID. In OpenTelemetry it is built into the metrics SDK.
2. **An exposition format that carries them.** The Prometheus **OpenMetrics** text format supports exemplars (`# {trace_id="..."} 0.42 1620000000`), and OTLP carries them natively. Plain Prometheus text format does **not**, so the endpoint must expose OpenMetrics and the scraper must request it.
3. **A scraper that ingests them.** Prometheus needs `--enable-feature=exemplar-storage` and an `Accept` header negotiating OpenMetrics. Exemplars are stored in a fixed-size in-memory circular buffer, so they are **short-lived** - typically minutes to hours, not days. That is a real limitation: you cannot chase an exemplar from last week.
4. **A backend that stores and queries them** - Prometheus, Mimir, Thanos, or a vendor equivalent, with the `/api/v1/query_exemplars` endpoint.
5. **A trace backend that has the corresponding trace.** This is the catch that breaks most implementations: if you sample traces at 1 percent, 99 percent of your exemplars point at trace IDs that were never stored, so clicking through gives "trace not found". **Exemplars and sampling must be designed together** - either sample high, or use tail-based sampling with a policy that keeps slow requests (which are exactly the ones exemplars point at).
6. **A UI that links them** - Grafana with a configured data source link from the Prometheus source to the Tempo/Jaeger source.

Point 5 is the one worth raising unprompted, because it is the difference between a feature that works and a feature that is demoed once.

### Q198. SLI, SLO, SLA and error budget

- **SLI** - a *measurement* of service behaviour, expressed as a ratio of good events to valid events. "The proportion of HTTP requests that completed successfully in under 300 ms."
- **SLO** - a *target* for an SLI over a window. "99.9 percent over 28 days."
- **SLA** - a *contract* with a customer, including consequences (refunds, credits). Always looser than the SLO, deliberately, so you have room to react before you breach the contract.
- **Error budget** - the allowed shortfall: `1 - SLO`. At 99.9 percent over 28 days that is **0.1 percent of requests**, or about **40 minutes** of total unavailability. It is a *budget* because it is meant to be spent - on releases, experiments and risk.

**A good availability SLI** for a request-driven service:

> The proportion of valid HTTP requests, measured at the load balancer, that return a non-5xx status within 300 ms, over a rolling 28-day window.

The parts that make it good, and the naive version's failures:

| | Naive | Good |
| --- | --- | --- |
| **Where measured** | On the server, in the application | **At the load balancer or the client.** A server-side metric cannot see requests that never arrived - a crashed pod, a DNS failure, an exhausted connection pool, an ingress outage. The naive SLI reports 100 percent during a total outage because zero requests were served and zero failed. |
| **What counts as bad** | 5xx only | **5xx *and* too-slow.** A request that takes 30 seconds and succeeds is a failure to the user. Latency belongs in the availability SLI, not as a separate afterthought. |
| **Denominator** | All requests | **Valid requests.** Exclude health checks, synthetic traffic, and 4xx caused by the client - a client sending malformed requests should not consume your error budget. Be careful: 429 and 401 caused by *your* misconfiguration should count. |
| **Aggregation** | Uptime, or a time-based average | **Event-based ratio.** "Minutes up" hides a failure affecting 10 percent of requests for a week. Ratios of requests reflect user experience. |
| **Window** | Calendar month | **Rolling window.** A calendar month resets the budget on the 1st, which produces a perverse incentive to take risk on the 30th and creates a cliff. |

The naive SLI is wrong primarily because **it is measured from inside the thing that fails**, which is the point worth leading with.

### Q199. 99.99 percent and complaining users `[T]`

1. **The SLI is measured in the wrong place.** Measured at the application, it counts only requests that reached it. Requests failing at DNS, the load balancer, the ingress, the mesh, or dropped because the connection pool was exhausted are invisible. During a partial outage the numerator and denominator fall together and the ratio stays beautiful. This is the most common cause.
2. **The aggregate hides the distribution.** 99.99 percent overall can be 100 percent for the 95 percent of traffic that is health checks and cheap reads, and 98 percent for the checkout endpoint - or 100 percent for most tenants and 70 percent for your largest customer. **Users experience their own slice, not the average.** A per-endpoint and per-tenant breakdown almost always tells a different story.
3. **The SLI does not measure what users care about.** Non-5xx within a latency bound is a proxy. A request returning 200 with an empty result set, a stale cache, a partial page, a failed background job, a payment that silently did not settle - all count as successes. The failures that generate complaints are frequently *correctness* failures, and no availability SLI sees them.
4. **The window is too long.** A rolling 28-day 99.99 percent absorbs a 40-minute total outage and still reports 99.90 percent for the month - a single number that is technically fine and describes a very bad Tuesday. Users remember the outage; the metric remembers the month. Burn-rate alerting (Q204) exists precisely because the window-level number is not an operational signal.

A fifth worth mentioning: **the complaint may not be about availability at all** - it may be about a feature regression, a UX change or an integration partner. Confirming that the complaints and the SLI are even measuring the same thing is the first move.

The response is to add SLIs where the gaps are: client-side or synthetic measurement, per-endpoint and per-tenant SLO breakdowns, and at least one **business-outcome SLI** (orders completed per minute versus baseline) which catches the "200 OK and wrong" class.

### Q200. Observability strategy on a fixed budget `[A]`

**Frame it as a portfolio.** Observability spend is not one thing; it is metrics (cheap, low-cardinality, long retention), logs (expensive, high volume, short retention), traces (expensive, high volume, sampled) and profiles (cheap, sampled). The budget question is how to allocate across them, and the default allocation in most estates is badly wrong - typically 70-80 percent on logs, which is the least efficient signal per pound.

**What I keep at full fidelity:**

- **Metrics for the RED/USE signals and everything in an SLO or an alert.** Metrics are two to three orders of magnitude cheaper per unit of information than logs. Anything that can be a metric should be a metric.
- **All errors** - error logs, error traces, exception detail. They are rare and they are the point.
- **Deployment, config and flag change events.** Tiny volume, enormous diagnostic value (Q182).
- **Audit logs** where compliance requires them - non-negotiable, and budgeted separately so they are never traded against operational logging.

**What I sample:**

- **Traces**: tail-based, keeping 100 percent of errors and slow requests and 1-5 percent of the rest (Q196). If tail-based is too much infrastructure for the estate, head-based at 5-10 percent with error-biased sampling.
- **`INFO` logs on high-volume paths**, deterministically by trace ID so sampled requests are complete (Q192).
- **Profiles**: continuous profiling at a low sampling rate is genuinely cheap and disproportionately useful.

**What I drop:**

- **Access logs duplicating request metrics.** If you have an RED histogram per route, per-request access logs are a very expensive duplicate. Keep them for errors only.
- **Health check and readiness probe telemetry** - filtered at the Collector, not at the backend, so you do not pay egress.
- **Debug-level logs in production**, entirely.
- **High-cardinality metric labels** - dropped at scrape or in the Collector (Q184), with the underlying need served by traces or a wide-event store instead.
- **Long metric retention at full resolution** - downsample beyond 30 days (Thanos/Mimir compaction), keep a small set of SLO and capacity series at long retention.

**Structural moves that cut cost without cutting signal:**

1. **An OTel Collector tier** so filtering, sampling and redaction happen **before egress** - you stop paying to transmit and ingest what you will not query (Q194). This is usually the single largest saving available.
2. **Tiered retention**: hot for 7-14 days where investigation actually happens, cold object storage beyond that for the rare deep query.
3. **Attribute the spend per team and make it visible** (Q250). Nothing reduces log volume like a team seeing their own number.
4. **A standard instrumentation library** so services emit a consistent, bounded set rather than each team inventing metrics - which is where cardinality explosions come from.

**Guardrails I would keep regardless of budget pressure**: SLO measurement, alerting-relevant metrics, error capture, audit logs, and change events. If the budget forces a cut into those, the correct response is to say the budget is too small and quantify what is being given up, rather than degrading them quietly.

*Hook: an observability cost reduction you led, and what you cut versus what you refused to cut.*

---

## 13. Alerting, on-call and incident response

### Q201. What makes a good alert

Criteria:

1. **It is actionable.** There is something a human can do right now. If the response is "watch it", it is a dashboard, not an alert.
2. **It requires a human.** If the response is deterministic, automate it and alert on the automation failing.
3. **It reflects user impact**, or is a strong leading indicator of it (Q202).
4. **It is urgent.** Waking someone is justified only if waiting until morning makes it materially worse.
5. **It is specific enough to act on**, with a link to a runbook and a dashboard, and a title that says what is wrong rather than which threshold was crossed.
6. **It is reliable** - it fires when the condition holds and not otherwise. An alert with a meaningful false-positive rate trains people to ignore it, which is worse than not having it.
7. **It has an owner.**

**The test I apply before adding one:**

> "What will the person paged by this actually *do*, at 3 am, and what happens if they do nothing until 9 am?"

If the answer to the first is "look at it and go back to sleep", it should not page. If the answer to the second is "nothing much", it should be a ticket. And the follow-up: **"is this already covered by a symptom alert?"** - most proposed alerts are causes that would be caught by an existing symptom alert, and adding them buys duplicate noise rather than coverage.

The second test is retrospective and more honest: **an alert that has fired ten times and never required action is deleted**, not tuned (Q206).

### Q202. Symptom versus cause alerting

**Symptom-based** alerts on what the user experiences: error rate, latency, throughput collapse. **Cause-based** alerts on a mechanism that might produce that: CPU high, disk filling, a queue growing, a pod restarting.

The argument for symptoms: there are a small number of ways a service can be bad for users and an unbounded number of ways it can be internally unusual. Alerting on causes gives you an unbounded alert set, most of which fire when nothing is wrong (a CPU spike that the service absorbed) and none of which fire for the failure nobody predicted. Symptom alerts have complete coverage by construction - if users are affected, the symptom alert fires, whatever the cause.

The counter-argument, and the reason it is not absolute: some causes are worth alerting on because **the symptom arrives too late to prevent**. A disk filling gives you hours of warning and a certain outage; waiting for the symptom means waiting for the outage. So: **page on symptoms, ticket on causes, and page on the small set of causes with a long fuse and a certain outcome.**

**The small set I would put on any request-driven service:**

| Alert | Type |
| --- | --- |
| **SLO error-budget burn rate**, multi-window (Q204) - covers both errors and latency if the SLI includes latency | Symptom, page |
| **Availability / total failure** - the service is returning nothing, or `up == 0` for all instances | Symptom, page |
| **Traffic collapse** - request rate far below the expected band. Catches the failures upstream of you, which no error-rate alert can see | Symptom, page |
| **Saturation with a long fuse** - disk predicted full within 4 hours, certificate expiring within 14 days, connection pool at 100 percent sustained | Cause, page or ticket by urgency |
| **Dependency SLO breach** for a critical downstream | Symptom of theirs, ticket unless it is breaching yours |

Everything else - CPU, memory, restarts, GC time, queue depth - goes on the dashboard and into the investigation, not into the pager.

### Q203. Golden signals, RED and USE

- **The four golden signals** (Google SRE): **latency, traffic, errors, saturation**. The general-purpose set for a user-facing system.
- **RED** (Weave): **Rate, Errors, Duration** - per *service* or per *endpoint*. It is the golden signals minus saturation, applied to request-driven work.
- **USE** (Brendan Gregg): **Utilization, Saturation, Errors** - per *resource*: CPU, memory, disk, network, and also logical resources like a thread pool or a connection pool.

**When each applies:**

- **RED for services**, because a service is defined by the requests it handles. It is what you build dashboards and SLOs on, and it is what your alerts should be based on.
- **USE for resources**, because a resource is defined by what it can supply. It is what you use when RED tells you something is wrong and you need to find the constraint.

**The overlap and what each misses:**

- **Errors appear in both**, but they mean different things: a service error is a failed request; a resource error is a device or driver error. Do not conflate them.
- **RED misses saturation**, which is why it is not sufficient on its own. A service at 100 percent thread-pool utilization has fine Rate, Errors and Duration right up until it does not - saturation is the leading indicator and RED has no equivalent.
- **USE misses the user.** A cluster with every resource comfortably utilized can be serving errors for a whole endpoint.
- **Both miss asynchronous work.** Neither describes a queue consumer well; there you want consumer lag, processing rate and age of the oldest unprocessed message, which is closer to USE applied to the queue.
- **Both miss correctness** (Q199). A service returning 200s with wrong data scores perfectly on all of them.

In practice: RED for every service, USE for every resource under it, saturation from USE promoted into the service's dashboard, and at least one business-outcome metric alongside.

### Q204. Multi-window multi-burn-rate alerting

**Burn rate** is the rate at which you are consuming the error budget, normalized so that **burn rate 1 = exactly exhausting the budget at the end of the window**. For a 99.9 percent SLO over 30 days, the budget is 0.1 percent of requests; an observed error ratio of 0.1 percent is burn rate 1, and 1 percent is burn rate 10.

The problem being solved: a fixed threshold on error rate is either too sensitive (paging for a blip) or too slow (a 0.2 percent error rate burns the entire budget in 15 days and never trips a 1 percent threshold). Burn rate makes the alert proportional to *consequence*.

**The standard configuration** (Google SRE workbook), for a 99.9 percent / 30-day SLO:

| Severity | Long window | Short window | Burn rate | Budget consumed before it fires | Time to exhaustion |
| --- | --- | --- | --- | --- | --- |
| **Page** | 1 hour | 5 min | **14.4** | 2% | ~2 days |
| **Page** | 6 hours | 30 min | **6** | 5% | ~5 days |
| **Ticket** | 1 day | 2 hours | **3** | 10% | ~10 days |
| **Ticket** | 3 days | 6 hours | **1** | 10% | 30 days |

The rule fires when **both** windows exceed the burn rate:

```
(rate_error_ratio[1h] > 14.4 * 0.001) and (rate_error_ratio[5m] > 14.4 * 0.001)
```

**What each part catches:**

- **The long window** determines *significance*: it is what makes the alert proportional to budget consumed, and it prevents paging for a 30-second spike that consumed 0.01 percent of the budget.
- **The short window is the reset condition**, and this is the part people omit and then wonder why alerts stay firing for an hour after recovery. Without it, a 1-hour window keeps the alert firing for a full hour after the incident ends, because the window still contains the bad data. Requiring the short window to *also* be burning means the alert clears within minutes of recovery.
- **The fast/high-burn pair (14.4 over 1h)** catches acute outages quickly - a total outage burns 2 percent of a monthly budget in about 43 minutes.
- **The slow/low-burn pair (3 over 1d, 1 over 3d)** catches the chronic degradation that never trips an acute threshold and quietly eats the month. These should ticket, not page, because there is no urgency - only significance.

The implementation detail that matters: precompute the error ratios for each window as **recording rules** (Q189), or the alerting rules become expensive and unreadable.

### Q205. Nightly 02:00 alert, always self-resolves `[T]`

**The wrong response** is to raise the threshold or add a delay until it stops firing. That silences the signal without understanding it, and it is how a real problem gets tuned into invisibility.

**The right response** is to find out what happens at 02:00, because something does. Candidates: a backup, a batch job, log rotation, a cron-driven report, a certificate renewal, an autoscaling scale-in, an index rebuild, a partner's nightly file drop, or a cloud maintenance window. Ten minutes of resolution suggests a bounded job rather than a fault.

Then one of four outcomes, and the point is that they are *different*:

1. **It is expected and harmless** - a batch job legitimately drives CPU up for ten minutes with no user impact. The alert is measuring the wrong thing: it should be a symptom alert on user impact (Q202), which would not fire. **Fix the alert to measure impact, not cause.** Not a threshold change - a change of subject.
2. **It is expected and does have user impact** - the nightly job degrades latency for real users in another timezone. That is a real defect. **Fix the job**: throttle it, move it to a replica, move it to a quieter hour, or accept it and record it against the error budget.
3. **It is unexpected.** Something is running that nobody knows about. That is worth finding, and it is occasionally something serious.
4. **It is genuinely a scheduled maintenance window** where degradation is agreed. Then it belongs in a **scheduled silence / mute timing** in Alertmanager, documented, with an expiry - not a permanently loosened threshold.

The general principle: **an alert that always self-resolves is either measuring the wrong thing or describing a real recurring defect.** Both need action; neither is fixed by tuning.

*Hook: a recurring alert whose cause turned out to be something nobody expected.*

### Q206. Alert fatigue

**How to measure it:**

- **Pages per on-call shift**, as a distribution. The often-quoted target is **fewer than two per shift**; more than five and people stop reading them.
- **Actionability rate** - the proportion of pages that resulted in a remediating action. This is the key metric, and it requires the responder to classify each page on resolution (one click: "acted" / "no action needed" / "false alarm"). Below ~70 percent actionable, you have a credibility problem.
- **Out-of-hours page count** specifically, since night pages cost far more than daytime ones.
- **Time to acknowledge**, trending upward - the clearest behavioural signal that people have stopped believing the pager.
- **Alert-to-incident ratio** and the distribution of pages by rule: it is almost always the case that three rules produce half the volume.
- **Auto-resolve rate** - pages that resolved before anyone looked.
- **A direct question in the on-call handover**: "was any of that useful?"

**Policy for an alert that has never required action:**

**Delete it.** Not tune it, not lower its severity indefinitely, not silence it - delete it, on a stated schedule (say, any paging alert with zero actionable fires in 90 days), with the deletion announced so the owner can object. Two supporting rules make this workable: deletions are reversible (it is a commit), and an owner who objects must state what action it would prompt - which is Q201's test applied retrospectively.

The two intermediate options, used deliberately rather than as avoidance: **demote to a ticket** if the condition is real but not urgent, and **fix the underlying flakiness** if the alert is right and the signal is noisy (wrong window, missing `for` duration, rate over too short a range).

The organizational point: alert deletion has to be **socially safe**. If removing an alert is seen as reckless, nobody will, and the set only grows. Framing it as "every alert we keep makes the others less likely to be read" is the argument that lands.

### Q207. Alertmanager routing to turn a cluster failure into one page

The four mechanisms:

- **Grouping** (`group_by`, `group_wait`, `group_interval`) - collapse alerts sharing labels into one notification. `group_wait` delays the first notification so related alerts arrive together.
- **Inhibition** - suppress alerts when a more significant alert is already firing, matched on shared labels.
- **Silencing** - time-bounded, manual or API-driven suppression, matched on labels.
- **Routing** - a tree matching on labels, deciding receiver, grouping and repeat behaviour.

**The configuration:**

```yaml
route:
  group_by: [alertname, cluster, service]
  group_wait: 30s          # collect related alerts before the first page
  group_interval: 5m       # batch subsequent changes to the group
  repeat_interval: 4h
  receiver: default
  routes:
    - matchers: [severity="critical"]
      receiver: pagerduty
    - matchers: [severity="warning"]
      receiver: slack

inhibit_rules:
  # A whole cluster down suppresses every service alert in it
  - source_matchers: [alertname="ClusterDown"]
    target_matchers: [severity=~"critical|warning"]
    equal: [cluster]

  # A node down suppresses pod-level alerts on that node
  - source_matchers: [alertname="NodeNotReady"]
    target_matchers: [alertname=~"Pod.*"]
    equal: [cluster, node]

  # A critical alert suppresses the warning-level version of itself
  - source_matchers: [severity="critical"]
    target_matchers: [severity="warning"]
    equal: [alertname, cluster, service]

  # A failed dependency suppresses its dependents' symptom alerts
  - source_matchers: [alertname="DatabaseDown"]
    target_matchers: [alertname="HighErrorRate"]
    equal: [cluster]
```

The design principles behind it:

1. **Group by the smallest label set that makes one notification coherent.** Grouping by `alertname, cluster` turns 200 pods failing into one page; grouping by `pod` gives you 200. The common mistake is including an instance-level label in `group_by`, which defeats grouping entirely.
2. **`group_wait` of 20-40 seconds** is what allows a cascading failure to arrive as one page rather than a page followed by 199 updates.
3. **Inhibition must follow the dependency hierarchy** - infrastructure suppresses platform suppresses application. This requires alerts to carry consistent `cluster`, `node` and `service` labels, which is a discipline in the *rules*, not in Alertmanager.
4. **The top-level cause alert must exist**, or there is nothing to inhibit with. `ClusterDown` and `NodeNotReady` earn their place solely as inhibition sources.
5. **`repeat_interval` long enough** not to re-page during an active incident that is already being worked.

### Q208. Paging, ticketing, dashboard-only

**My rule:**

| Route | Criterion |
| --- | --- |
| **Page** | User impact is happening or is certain within hours, **and** a human action now materially changes the outcome. |
| **Ticket** | The condition is real and needs action, but tomorrow morning is fine. Chronic burn, capacity trends, non-urgent saturation, a degraded redundant component. |
| **Dashboard only** | Informational, or diagnostic context used during an investigation. Anything you would look at *because* you were paged. |

The two questions that decide it are from Q201: what would the responder do, and what happens if nobody acts until 09:00.

**Who decides**: the **service owner proposes**, and the **on-call team has a veto**. That combination matters. The owner has the context to judge severity; the people carrying the pager have the standing to refuse noise, and giving them that standing is what keeps the alert set honest. In practice this means alert rules are code in the service's repository, reviewed by the team, with the on-call rotation as a required reviewer for anything that pages.

I would add two structural rules. **Adding a paging alert requires a runbook link** - if you cannot write down what to do, it should not wake anyone. And **severity is reviewed in the postmortem**: an incident where a ticket-level alert should have paged, or where a page was useless, produces a change to the routing, so the classification improves from evidence rather than from opinion.

### Q209. On-call rotation design

**What makes a rotation sustainable at 19 people versus 5:**

At 19, a weekly primary rotation means each person is on call about **2.7 weeks a year** - infrequent enough to be tolerable, frequent enough to stay familiar. You can run primary and secondary tiers, and you can exclude people who are new or on leave without breaking the schedule.

At 5, weekly rotation means **10 weeks a year each**, one week in five. That is unsustainable for anything but a very quiet service, and it is the number that drives attrition. The available levers at 5 are: shorten shifts (a 3-4 day rotation reduces the recovery cost of a bad week even though the annual total is the same), share the rotation with another team, buy a follow-the-sun partner, or - most importantly - **reduce the page volume until one-in-five is genuinely quiet**. At small team sizes, on-call load is fixed by alert hygiene rather than by scheduling.

**Design elements:**

- **Size**: at least 6 people for a 24×7 primary rotation; 8+ to be comfortable. Below 6, on-call is a retention risk and should be treated as one.
- **Shift length**: one week is standard and matches the handover cadence. Shorter shifts reduce burnout per shift and increase handover overhead; for a noisy service, shorter is better.
- **Tiers**: a primary who responds and a secondary who is the escalation path, plus a named incident commander for major incidents. The secondary is what makes a single unreachable phone survivable.
- **Handover**: a scheduled, mandatory handover meeting with a written summary - what fired, what is still open, what is fragile, what is planned. The handover document is the single highest-value artefact in the whole system and it is the one most often skipped.
- **Follow-the-sun** removes night pages entirely, which is the biggest single quality-of-life improvement available. It requires two or three sites with genuine ownership and shared context, which is a large organizational investment - and it fails badly if one region is a "night shift" without real ownership. With teams in India and the US, this is often achievable and worth pushing for.
- **Compensation**: on-call must be paid or time-compensated, explicitly. Beyond fairness, it makes the cost of a noisy service **visible on a budget line**, which is the most reliable mechanism I know for getting alert hygiene prioritized.
- **Guardrails**: a right to sleep after a bad night, protected recovery time, and a rule that the on-call person is not also on the sprint's critical path.

### Q210. Incident command

**Roles:**

- **Incident Commander** - owns the incident. Decides, delegates, keeps the timeline, decides on escalation and on customer communication. Does **not** debug.
- **Operations / Tech Lead** - owns the technical investigation and remediation, directs the responders doing hands-on work.
- **Communications Lead** - internal and external updates, status page, stakeholder management.
- **Scribe** - maintains the timeline: what was observed, what was tried, what was decided, when. Often merged with Comms in smaller incidents.
- **Subject matter experts** - pulled in as needed, and released when done.

For a small incident one person holds several roles; the discipline is that the roles are **named and known**, so nobody has to ask who is deciding.

**Who declares**: **anyone can declare an incident, and that must be true and safe.** The failure mode you are designing against is an engineer who suspects something is badly wrong and hesitates because declaring feels like an overreaction. Making declaration cheap and blameless - and explicitly praising false-positive declarations - is worth more than any tooling. The first responder is IC by default until they hand it over.

**Why the person fixing it should not be the one communicating:**

1. **Debugging is deep focus; communication is constant interruption.** Doing both means doing neither. The interruption cost is the real one - a stakeholder asking "any update?" every five minutes destroys the investigation.
2. **The two have different clocks.** Stakeholders need updates on a predictable cadence (every 20-30 minutes) whether or not there is news. An engineer mid-investigation will not produce those, and silence generates escalation, which generates more interruption.
3. **They need different content.** A responder communicates mechanism; stakeholders need impact, scope, ETA and what they should do. Translating between the two is a skill and a job.
4. **Judgement under load degrades**, and the person deepest in the technical problem is the least well placed to decide whether to fail over, roll back, or tell customers - decisions that need someone holding the whole picture rather than the current hypothesis.
5. **Accountability is clearer.** One person owning the decision prevents the two-engineers-conflicting-fixes failure of Q212.

### Q211. Severity definitions

Written for a non-engineer at 03:00 - the test is whether an on-call person can classify in ten seconds without judgement calls.

**SEV1 - Critical.** *Customers cannot use the product, or money or data is at risk.*
- The service is down or unusable for most customers.
- Customers cannot complete a core action (log in, pay, place an order).
- Data is being lost, corrupted, or exposed to the wrong people.
- A security breach is suspected or confirmed.
- **Response**: page immediately, incident commander appointed, all-hands as needed, customer communication within 30 minutes, updates every 30 minutes. Wake whoever is needed.

**SEV2 - Major.** *The product works, but significantly worse, or an important part of it is broken.*
- A major feature is unavailable but the core flow works.
- Severe degradation - things are very slow but succeeding.
- One large customer, one region, or one significant segment is affected.
- A redundancy has been lost, so the next failure becomes a SEV1.
- **Response**: page during business hours; out of hours, page if it is worsening or if it puts the SLO at risk. IC appointed, updates hourly.

**SEV3 - Minor.** *Something is wrong; customers mostly are not noticing.*
- A minor feature is broken, or there is a workaround.
- A small number of customers or a low-traffic path is affected.
- An internal tool is down.
- **Response**: a ticket, worked in business hours. No page.

**Two rules that make it work in practice:** when in doubt, **declare the higher severity** - downgrading is easy and free, upgrading late is expensive. And severity is about **impact, not cause**: a database failure that customers cannot detect is not a SEV1, and a CSS bug that prevents checkout is.

### Q212. Two engineers, conflicting fixes `[T]`

**The process failure is that nobody owned the decision, and there was no single record of what was being changed.** Concretely, three things were missing:

1. **No incident commander.** Two competent engineers both saw a problem and both acted - which is exactly what you would expect without someone whose explicit job is deciding what gets done. This is the primary failure.
2. **No declared "one change at a time" discipline.** Even with an IC, if changes are not announced before they are made, you get concurrent mutation. And once two changes land together, you have destroyed your ability to attribute the outcome - if things improve, you do not know which one worked; if they worsen, you do not know which to revert.
3. **No single channel of record.** Work happening in DMs, in two terminals and in someone's head rather than in one incident channel means neither engineer knew what the other was doing.

**What prevents it:**

- **Appoint an IC immediately, even for small incidents**, and make it explicit in the channel: "I am IC". The IC's core function is exactly this - serializing action.
- **Say it before you do it.** A stated norm: every mutating action is announced in the incident channel *before* execution, in the form "I am going to X, any objection?" - and the IC acknowledges. This costs ten seconds and it is the single most effective control.
- **One change at a time, then observe.** Deliberately serialize so the effect of each action is attributable. This feels slow under pressure and is faster overall.
- **A shared timeline** maintained by the scribe, so the state of the world is written down rather than distributed across people's memories.
- **Access as a deliberate step**: for high-risk actions (a failover, a data mutation), require the IC's explicit go-ahead, and consider a two-person rule.

**In the postmortem**, the action item is not "communicate better" - it is a concrete change: the incident process document names the IC role and the announce-before-acting rule, the incident channel is created automatically by the paging tool with the roles posted in the topic, and the practice is rehearsed in game days (Q223) rather than learned during a real incident.

### Q213. Blameless postmortems

**What makes them work:**

- **Genuine psychological safety**, demonstrated rather than declared. The test is whether an engineer can say "I ran the wrong command against production" and the conversation moves immediately to *why the system allowed it* and *why it was not obvious it was wrong*. One instance of blame - even implied, even from a skip-level in the room - and every subsequent postmortem is a defensive document.
- **Focus on the system, not the person.** The question is never "why did you do that" but "what made that the reasonable action given what you knew at the time". Human error is a *symptom* of system design, not a root cause.
- **Counterfactual discipline.** "If only they had noticed" is not analysis. What made noticing hard?
- **A factual timeline first**, including what people believed at each moment, not just what was true. The gap between the two is where the learning is.
- **Multiple contributing causes, not a root cause.** Real incidents have a chain and a set of conditions. "Root cause: human error" is a sign the analysis stopped early.
- **Written by the people involved**, reviewed by others, and published widely enough that people outside the team learn from it.
- **A named facilitator** who is not from the affected team, which keeps it honest.

**What makes them theatre:**

- Held to satisfy a process requirement, with a template filled in and filed.
- A "root cause" that is a person, or "lack of testing", or "insufficient monitoring" - non-specific causes that generate non-specific actions.
- Action items that are aspirations ("be more careful", "improve documentation") rather than changes.
- Nobody outside the team reads it.
- Blameless in name while the individual is quietly counselled afterwards, which everyone finds out about.
- Held weeks later, when memory has decayed and urgency has gone.

**Tracking actions to completion** - the part where most programs fail:

1. **Every action has an owner, a due date and a ticket in the normal backlog**, not a separate postmortem tracker nobody looks at.
2. **Actions are classified by type**: prevent recurrence, reduce detection time, reduce recovery time, reduce impact. A postmortem with only "prevent" actions has not thought about the failure it did not anticipate.
3. **Prioritized against the severity**: SEV1 actions get committed capacity in the next sprint, not "when we have time".
4. **A visible aging report** - open postmortem actions by age and severity - reviewed at a regular management cadence. Visibility is what actually gets them done.
5. **A repeat incident triggers a review of the previous postmortem's actions**, and the question "did we do what we said?" - which is uncomfortable, which is the point.
6. **Accept that not everything will be done**, and close the ones you are deliberately not doing with a stated reason. An unbounded list of open actions is indistinguishable from having none.

### Q214. Runbooks

**What belongs in one:**

- **What this alert means**, in one sentence, and what user impact it corresponds to.
- **How to confirm it is real** - the specific dashboard, the specific query. The first thing an engineer needs at 3 am is to know whether this is genuine.
- **The immediate mitigation** - the action that stops customer impact, even if it does not fix the cause. Restart, fail over, scale up, flip the flag, roll back. This should be at the top, because it is what is needed first.
- **Diagnosis steps** - specific commands and queries, copy-pasteable, in order, with what each result means.
- **Escalation** - who to call, when, and what to tell them.
- **What not to do** - the actions that look helpful and make it worse. This section is disproportionately valuable and almost always missing.
- **Links** to the dashboard, the service's architecture summary, and recent related incidents.

**What does not belong**: architecture explanation, background theory, anything the reader is expected to read *before* the incident. A runbook is a checklist for a stressed person, not a document.

**What makes them rot**: they are written once at the end of an incident and never touched; they reference dashboards, hostnames and commands that change; they describe a system that has since been rearchitected; and nobody reads them until the next incident, so the rot is undetected until precisely the wrong moment.

**Keeping them accurate:**

1. **Link the runbook from the alert** (`runbook_url` annotation), so it is opened on every fire. A runbook nobody opens cannot be corrected.
2. **Correct it during the incident.** The norm: whoever used it fixes it before closing the incident, while the gap is fresh. This is the single most effective mechanism.
3. **Keep it in the service's repository**, reviewed with code, so a change that invalidates a step is visible in the same PR.
4. **Prefer executable to prose.** A script or a documented command is self-verifying in a way that a paragraph is not; better still, automate the step and let the runbook say "run this job".
5. **Exercise them in game days** (Q223) - the fastest way to discover that a runbook is fiction.
6. **A staleness signal**: a runbook not touched in a year on an alert that fired three times is either perfect or wrong, and it is worth a five-minute check.
7. **No runbook, no page** (Q208), which stops the set growing faster than it can be maintained.

### Q215. 4 am pages three nights a week `[A]`

Morale is collapsing because the pages are unbounded and there is no evidence that anyone is going to stop them. So the first two weeks have to produce a visible reduction *and* a visible commitment; the quarter fixes the causes.

**First two weeks - reduce the volume, fast, and take the load off people.**

1. **Get the data.** Every page for the last 90 days: which rule, what time, was it actionable, what was done. This takes a day and it will show that a small number of rules produce most of the volume. Without this you are guessing.
2. **Ruthlessly triage the noisiest rules.** For each of the top rules: delete if never actionable, demote to a ticket if not urgent, fix the rule if it is right and noisy (wrong window, missing `for`, cause-based rather than symptom-based - Q202). I would expect to cut night pages by half in the first week, and I would say so publicly with the number.
3. **Add inhibition and grouping** (Q207) so a cascading failure is one page rather than twenty. Often the "three nights a week" is fewer distinct events than it appears.
4. **Immediate relief on the rotation**: add a second person to share the load, bring in a manager or a senior engineer to take shifts, or temporarily route non-critical alerts to a daytime queue. The team needs to sleep this week, not next quarter.
5. **Announce the plan and the commitment** - specifically, that on-call load is now a tracked metric with a target and dedicated capacity, and that fixing it takes priority over feature work until it is under control. Morale recovers on the *commitment* faster than on the result.
6. **Protect recovery time** immediately: anyone paged after midnight starts late or takes the day.

**First quarter - fix the causes.**

7. **Reserve capacity explicitly** - a fixed percentage of the sprint for reliability work, defended. Without this, step 8 does not happen.
8. **Work the top causes, not the top alerts.** Cluster the pages by underlying cause and fix the top three: the service that OOMs weekly, the job that fails on a schedule, the dependency with no retry, the disk that fills. Each fix removes a class of page permanently.
9. **Automate the deterministic responses.** Anything where the runbook says "restart it" or "scale it up" should be automated, with an alert only if the automation fails (Q201).
10. **Introduce SLO-based alerting** (Q204) to replace threshold alerts, so the pager reflects user impact and burn rate rather than machine conditions. This usually produces the largest structural reduction.
11. **Runbooks for everything that still pages** (Q214), which makes the remaining pages faster and less stressful even before the volume falls further.
12. **Make on-call load visible to leadership** as a metric with a target - pages per shift, out-of-hours pages, actionability rate - reported alongside delivery metrics. This is what stops it regressing once attention moves on.
13. **Review the rotation design** (Q209) - size, shift length, compensation, and whether follow-the-sun is achievable.

**What I would not do**: raise thresholds until the pager is quiet, or tell the team to "push back on alerts" without giving them the authority and the capacity to actually remove them.

*Hook: an on-call load reduction you drove, with the before and after page counts.*

---

## 14. Reliability engineering - capacity, chaos, backup and DR

### Q216. Availability targets in minutes

| SLO | Downtime per 30 days | Per week | Per year |
| --- | --- | --- | --- |
| **99%** | 7 h 12 m | 1 h 41 m | 3 d 15 h |
| **99.9%** ("three nines") | **43 m** | 10 m 5 s | 8 h 46 m |
| **99.95%** | **21.6 m** | 5 m 2 s | 4 h 23 m |
| **99.99%** ("four nines") | **4.3 m** | 1 m 1 s | 52 m 36 s |
| **99.999%** | 26 s | 6 s | 5 m 15 s |

**What each implies operationally:**

- **99.9%** - 43 minutes a month. A human can be paged, wake up, log in, diagnose and act within the budget, but only once or twice. Achievable with a single region, standard redundancy, rolling deployments and a competent on-call rotation. This is the right target for most internal and many external services.
- **99.95%** - 21 minutes. A human can still respond, but only for one incident, and you cannot afford a slow diagnosis. Requires automated rollback, good runbooks, and no single points of failure within the region.
- **99.99%** - **4.3 minutes a month, which is less than the time it takes to wake up.** This is the threshold where human response stops being part of the recovery path. It requires automated detection and automated remediation, multi-AZ as a minimum and usually multi-region, no dependency that is not itself at four nines, and - critically - **deployments that cannot cause it**, meaning progressive rollout with automated abort. It also changes the maintenance model: you cannot take anything down.
- **99.999%** - 26 seconds a month. Realistically achievable only for narrow, stateless, heavily-engineered components. For a business application it is almost never a real requirement (Q231).

The number worth internalizing for interviews: **99.99 percent means every incident must be resolved automatically**, and that is the sentence that reframes the whole conversation with a business stakeholder.

### Q217. Composing dependency availability

For **sequential** (serial) dependencies - every one must work for the request to succeed - availabilities multiply:

```
0.999^5 = 0.99501
```

So **99.5 percent**, which is **3.6 hours of downtime a month** - eight times the budget of any individual dependency. Five dependencies at three nines cannot deliver a three-nines service, and this arithmetic is the reason "just add a microservice" has a cost that never appears in the design review.

**What changes it:**

- **Redundancy in parallel.** Two independent instances of a 99.9 percent dependency give `1 - (0.001)² = 99.9999 percent` - *if* the failures are genuinely independent, which they usually are not (shared AZ, shared deployment, shared config, shared dependency).
- **Making a dependency optional.** A dependency you can fail open on - a recommendation service, an enrichment call, a cache - is removed from the product entirely. `03-microservices` Q114-115 covers graceful degradation; here the point is that it is the single most effective lever, because it changes the *structure* rather than the numbers.
- **Caching.** A cached response means the dependency's downtime only affects the cache-miss fraction, so a 95 percent hit rate turns a 0.1 percent failure into a 0.005 percent one.
- **Retries and timeouts** convert some failures into latency, which helps if the failures are transient and independent, and does nothing (or amplifies - `03-microservices` Q106) if they are not.
- **Asynchrony.** Making a call a queued message removes it from the request path's availability chain entirely.
- **Correlated failure** works the other way: if all five dependencies share an AZ, a database or a deployment pipeline, the real availability is worse than the product suggests, because one event takes several down together.

The framing to give: **serial dependencies compose multiplicatively and that is brutal; the fix is almost never "make each dependency more reliable" and almost always "have fewer of them in the request path".**

### Q218. Capacity planning from a forecast

**The method:**

1. **Establish the unit of work and its cost.** From a load test or from production: at what request rate does one pod saturate, and what is the limiting resource? "One pod serves 200 rps at 70 percent CPU with p99 within SLO" is the number everything else builds on. Measure it; do not derive it.
2. **Convert the forecast into peak concurrency, not average.** Take the forecast's peak rate - usually daily peak, plus a seasonal multiplier - and apply Little's Law (`concurrency = arrival rate × latency`) to size thread pools and connections. Average rate is the wrong input; systems fail at peak.
3. **Compute base capacity**: `peak rate / per-pod capacity`, rounded up.
4. **Add headroom** (below).
5. **Check every downstream constraint** at that load: database connections, third-party rate limits, cache capacity, queue throughput, NAT gateway and load balancer limits. The service is rarely the binding constraint, and this step is the one that gets skipped.
6. **Re-derive at intervals**, because per-pod capacity changes with every release.

**Headroom**, and this is the part with real judgement in it:

- **Utilization target**: run steady-state at **50-70 percent** of saturation. Not because 90 percent does not work, but because queueing theory means latency rises non-linearly as you approach saturation - at 90 percent utilization, a 10 percent traffic increase produces a very large latency increase.
- **Failover headroom**: enough spare capacity to absorb the loss of a failure domain. Across 3 AZs, losing one means the remaining two take 50 percent more load each, so you need **N+1 sizing at the AZ level** - roughly 1.5× the base. For active-active across 2 regions, each region must carry 100 percent, so 2× total.
- **Spike headroom**: enough to survive the time it takes to autoscale (Q114) - three to eight minutes of growth at the fastest realistic ramp rate.
- **Deployment headroom**: `maxSurge` needs somewhere to go (Q85).

These compound but do not simply multiply - the largest usually dominates. In practice: size for peak, at 60 percent utilization, with N+1 across AZs, which lands around **2-2.5× the naive average-load number**. That gap is what capacity planning conversations are actually about.

### Q219. Load, stress, soak and spike tests

| Test | Question it answers |
| --- | --- |
| **Smoke** | Does the system work at all under trivial load? A pipeline gate. |
| **Load** | Does it meet SLOs at expected peak? Sustained, realistic mix, 15-60 minutes. |
| **Stress** | Where does it break, and *how*? Ramp past capacity until failure. The valuable output is the failure mode - graceful degradation or collapse. |
| **Soak** (endurance) | Does it stay healthy over hours or days at moderate load? |
| **Spike** | Does it survive a sudden 5-10× jump, and does it recover? |

**What a soak test catches in a JVM that a load test never will:**

1. **Memory leaks.** A slow leak - an unbounded cache, a listener never deregistered, a `ThreadLocal` in a pooled thread, a growing static collection - is invisible in 30 minutes and fatal in 12 hours. The signature is old-generation occupancy after full GC trending upward, which requires hours of data to see.
2. **Metaspace and class-loader leaks** (Q75), which grow with cumulative work, not with rate.
3. **Native and direct memory growth** - Netty buffers, native library allocations - which never appears on a heap graph and takes hours to reach the container limit.
4. **GC degradation over time.** Heap fragmentation, humongous allocations in G1, and a gradually rising full-GC frequency. A short test runs entirely in the well-behaved early phase.
5. **Resource handle leaks** - file descriptors, connections, threads - which accumulate slowly and fail suddenly at a limit.
6. **Connection pool and keep-alive pathologies** that only manifest after connections have aged past `maxLifetime` or a firewall's idle timeout.
7. **Cumulative external state**: a log disk filling, a temp directory growing, a queue with a slow drift between produce and consume rate, a database table growing until a query's plan flips (`06-database` Q78).
8. **Scheduled interference** - a nightly job, a certificate rotation, a token expiry at 60 minutes. Anything with a period longer than the test simply does not exist in a load test.

The rule of thumb: a soak test must run longer than your longest natural cycle - so at least 12-24 hours, and ideally across a token expiry and a scheduled job.

### Q220. Passed at 3×, fell over at 1.2× `[T]`

1. **The traffic mix was wrong.** The test hammered the cheap endpoints (a health check, a cached read) at high rate. Production traffic has a long tail of expensive operations - a report, a large payload, a cold cache, a specific tenant's data volume - and the *cost-weighted* load was far higher than the request count suggested. This is the most common cause by a wide margin.
2. **The data was wrong.** A test database with 10,000 rows behaves nothing like production with 200 million: different query plans, different index depth, different cache hit rates. Small, uniform, freshly-loaded test data hides every data-dependent failure.
3. **Caches were unrealistically warm - or cold.** A test looping over 100 test users has a 100 percent cache hit rate that production never sees. Conversely a test that never warms the JIT measures a system that does not exist in production.
4. **The environment was not production.** Fewer or different downstream dependencies (stubs instead of real services), no service mesh, no sidecars, different instance types, no noisy neighbours, different network topology, no TLS. Every stub is a dependency whose latency and failure behaviour you did not test.
5. **The load generator was the bottleneck**, or was too few clients. A test driving 3× from 20 connections has entirely different concurrency characteristics from production's 20,000 clients - connection pool behaviour, keep-alive, TLS handshake rate, and per-connection state all differ.
6. **No concurrent real-world conditions.** Production at 1.2× was simultaneously running a deployment, a backup, an autoscaling event, a batch job and a partner integration. The test ran in a quiet system.
7. **Shared downstream capacity.** The test service had the database to itself; in production it shares connection slots, IOPS and cache with everything else, so its effective capacity is much lower.

The corrective practice: **replay real production traffic** (shadow or recorded), against **production-shaped data**, in an environment with the **real dependencies**, and run it **while a deployment is happening**. And treat the load test's result as a bound on the failure mode, not as a capacity number - the durable value of a load test is discovering *how* it breaks, which is Q222's territory.

### Q221. Performance testing in the pipeline

The tension: performance is noisy, and a noisy gate gets disabled. So assert only on things that are **robust to noise** or **compared against a control**.

**What you can assert automatically:**

1. **Regression against a baseline run in the same job, on the same runner, at the same time.** Run old and new versions side by side and compare - this cancels most environmental noise, and it is the single technique that makes pipeline performance testing viable. Assert on the *ratio*, with a generous threshold (say, 20 percent worse fails).
2. **Coarse thresholds far from the noise floor.** "p99 under 2 seconds" when production is 200 ms catches catastrophic regressions and never flaps. A gate at "p99 under 210 ms" will flap daily.
3. **Resource assertions**, which are less noisy than latency: peak heap, allocation rate per request, thread count, connection count. An allocation-rate regression is a reliable early signal of a latency regression and is far more stable to measure.
4. **Counting rather than timing.** Assert on **number of database queries per request** (catches N+1 - `06-database` Q227), number of downstream HTTP calls, number of cache lookups. These are deterministic, noise-free, and catch the majority of real performance regressions at their cause. This is the most under-used technique on the list.
5. **Correctness under concurrency** - run the functional suite at concurrency and assert no errors. This finds race conditions and pool exhaustion, and it is a pass/fail rather than a measurement.
6. **Trend reporting without gating.** Record every run's numbers, chart them, and alert on a sustained shift. Not a gate, but it catches the slow drift that no single-run gate ever will.

**What does not work as a gate**: absolute latency thresholds on a shared runner; anything requiring a long soak (Q219 belongs on a schedule, not a PR); and full-scale load tests, which are too slow and too expensive per commit. Those go to a nightly or pre-release job against a production-like environment.

### Q222. Chaos engineering

**The steady-state hypothesis** is the foundation: before injecting anything, define a measurable, aggregate property of normal behaviour - "the checkout success rate stays above 99.5 percent and p99 latency stays below 400 ms". The experiment then states: *when I inject this failure, the steady state will be maintained.* You are testing a belief about the system's resilience, not "seeing what happens". If you cannot state the hypothesis, you are not doing an experiment; you are causing an incident.

It must be a **business or user-facing metric**, not a system metric. "CPU stays under 80 percent" is not a steady state anyone cares about.

**Blast radius control:**

- **Start in non-production**, but understand that non-production findings are weak - the interesting failures are in production's scale, traffic and dependency graph.
- **Smallest possible scope first**: one pod, then one AZ, then one service. Never start at the level you eventually want to test.
- **A defined, small fraction of traffic or infrastructure**, and a defined time window.
- **An abort condition defined in advance**, monitored automatically, with an **automatic stop** when the steady state breaks. A manual abort is not fast enough.
- **A tested kill switch** for the experiment itself - and it must not depend on the thing you are breaking.
- **Off-peak, announced, with the team watching.** Unannounced chaos is a political disaster and produces no better data.

**What you must have in place before the first experiment:**

1. **Observability good enough to measure the steady state in real time.** If you cannot see the effect within seconds, you cannot abort in time. This is the hard prerequisite, and most teams that want to do chaos are not ready on this axis.
2. **A mature incident process**, because you will cause an incident eventually.
3. **The ability to stop and to recover** - fast rollback, and confidence that the injected failure is reversible.
4. **Known, documented resilience mechanisms to test.** Chaos verifies that timeouts, retries, circuit breakers and fallbacks work. If they do not exist yet, build them first - injecting failure into a system with no resilience produces a predictable outage and no learning.
5. **Organizational buy-in**, explicitly, from whoever owns the customer impact.
6. **Fix the known problems first.** If you already have a list of known single points of failure, chaos will find them and you will have spent effort learning what you knew.

### Q223. Game days and failure injection

A **game day** is a scheduled exercise where a team responds to an injected or simulated failure using the real process, the real tools and the real runbooks. Its purpose is at least as much about testing **the humans and the process** as the system - detection, escalation, communication, decision-making - which is why it is different from an automated chaos experiment.

**What I would inject first, for a Kubernetes-hosted estate**, in order of value:

1. **Kill a pod, then all pods of one service.** The trivial one - and it reliably finds broken graceful shutdown (Q90), missing PDBs, single replicas, and stateful assumptions. *Expect to learn*: whether connection draining actually works.
2. **Kill a node.** Tests PDBs, rescheduling, volume reattachment (Q111), and whether capacity headroom is real. *Expect to learn*: how long a stateful pod actually takes to come back, and that it is much longer than anyone assumed.
3. **Fail an availability zone** - cordon and drain every node in one AZ. This is the highest-value experiment for most estates, because AZ failure is the most likely real infrastructure event. *Expect to learn*: that topology spread was aspirational, that a stateful dependency is single-AZ, and that N+1 capacity was not actually provisioned.
4. **Degrade a dependency**: inject 500 ms of latency, then a 50 percent error rate, into a downstream service. *Expect to learn*: that timeouts are too long or absent, that retries amplify (`03-microservices` Q106), and that a circuit breaker configured for failures does nothing for slowness (`03-microservices` Q108).
5. **Take a dependency down completely** - the cache, then a non-critical service. *Expect to learn*: whether "non-critical" is true. It usually is not.
6. **DNS failure or CoreDNS degradation.** Disproportionately common in reality and disproportionately damaging (Q105). *Expect to learn*: that the JVM cached a dead address forever.
7. **Exhaust a resource**: fill a disk, exhaust a connection pool, saturate CPU on one node. *Expect to learn*: whether the failure is graceful or a cascade.
8. **A process failure with no technical injection at all**: "the primary on-call is unreachable" or "the observability stack is down - diagnose without dashboards". These consistently produce the most uncomfortable and most valuable findings.

The output of a game day is a postmortem with actions, exactly like a real incident, plus a set of corrections to the runbooks that were found to be wrong (Q214).

### Q224. RPO and RTO

- **RPO - Recovery Point Objective**: the maximum acceptable **data loss**, expressed as time. RPO of 15 minutes means you can lose up to 15 minutes of the most recent writes.
- **RTO - Recovery Time Objective**: the maximum acceptable **time to restore service** after a disaster.

**They drive different parts of the architecture, and this is the point of the question:**

**RPO drives the *data replication* strategy** - how often and how synchronously data leaves the primary:

| RPO | What it requires |
| --- | --- |
| Hours | Nightly backups, or periodic snapshots |
| Minutes | Continuous log shipping / asynchronous replication, or frequent incremental backups plus WAL archiving |
| Seconds | Asynchronous streaming replication with low lag |
| **Zero** | **Synchronous replication** - the write is not acknowledged until a second site has it. This directly costs write latency (a cross-region round trip) and availability (the primary cannot commit if the secondary is unreachable, unless you allow it to degrade - which reintroduces data loss). |

**RTO drives the *standby capacity and automation* strategy** - how much infrastructure is already running and how much of the failover is automatic:

| RTO | What it requires |
| --- | --- |
| Days | Restore from backup into rebuilt infrastructure |
| Hours | Infrastructure as code that can rebuild the environment, plus a rehearsed restore |
| **Under an hour** | Pilot light or warm standby - infrastructure exists, data is replicated, scale-up and cutover are scripted |
| **Minutes** | Warm standby with automated failover, DNS/global routing already in place, and a tested decision procedure |
| **Seconds** | Active-active - there is no failover, only traffic shifting |

The two are independent: you can have RPO of seconds and RTO of a day (data is safely replicated, but nothing is standing by to serve it), or RPO of a day and RTO of minutes (a warm standby serving yesterday's data). Conflating them is the most common mistake in a DR conversation, and asking for both to be near zero without understanding that each has a separate, large bill is the second.

### Q225. Successful backups for two years `[T]`

**A successful backup job proves that a process wrote some bytes somewhere and exited zero.** It does not prove:

- that the bytes are **readable** - corruption, truncation, a partial write, a failed compression step;
- that they are **complete** - a backup that silently excluded a table, a schema, a new database created eighteen months ago, or a volume nobody added to the job;
- that they are **restorable** - the restore procedure may not exist, may not work on the current engine version, or may require a credential or an encryption key nobody has;
- that they are **consistent** - a filesystem snapshot of a running database without quiescing, or a multi-volume system snapshotted at different instants, may restore to a state that never existed;
- that the restore fits the **RTO** - a 4 TB restore that takes 14 hours does not satisfy a 2-hour RTO no matter how good the backup is;
- that they are **decryptable** - the KMS key was rotated, or is in the account you just lost;
- that they **survive the disaster** - backups in the same region, same account, or same blast radius as the primary. Ransomware and a compromised account both take the backups too, unless they are immutable and isolated.

**What is evidence:**

1. **A restore, performed, with the result verified** - the data is queryable, row counts and checksums match, the application starts against it and passes a smoke test. Automated, on a schedule (weekly or monthly), into a scratch environment.
2. **A measured RTO from that restore** - wall clock, recorded as a metric, trended. This is the number you report, and it will be larger than anyone's estimate.
3. **A measured RPO** - the timestamp of the newest recoverable transaction in the restored copy.
4. **A full disaster rehearsal** at least annually: restore into a rebuilt environment from infrastructure code, with the people who would actually do it, without access to the primary.
5. **Backup integrity checks** - checksums verified, and for databases the engine's own verification (`pg_verifybackup`, `RESTORE VERIFYONLY`).
6. **Alerting on backup *age* and *size*, not just job success.** A backup that succeeded and is 4 KB, or whose newest file is nine days old, is a failure that a success/failure alert misses entirely.
7. **Isolation and immutability proven** - object lock enabled, cross-account, and tested that the primary's credentials cannot delete them.

The line worth saying: **you do not have backups, you have restores** - and until you have performed one, you have neither.

*Hook: a restore you performed or a drill you ran, and how the measured RTO compared to the documented one.*

### Q226. Backup strategy for a Kubernetes estate

**First, what is actually stateful** - and the answer for most estates is: less in the cluster than people think.

- **Application data** lives in managed services - RDS, DynamoDB, S3, Kafka, Elasticache. **These are backed up by their own mechanisms**, not by anything Kubernetes-aware, and they are the things whose loss is unrecoverable. This is where the backup strategy actually matters.
- **In-cluster persistent volumes** - anything running a database, a queue or a stateful system inside the cluster. Real state, and the hardest to back up correctly.
- **etcd** - the cluster's own state.
- **Everything else - Deployments, Services, ConfigMaps** - is **not state**; it is a projection of git (Q149). It should not need backing up at all, and if it does, that is a signal that GitOps is incomplete.

**What Velero includes and excludes:**

*Includes*: Kubernetes API objects (filtered by namespace, label or resource type), and PersistentVolume data - either via **CSI volume snapshots** (fast, cloud-native, but the snapshot lives in the cloud provider and is usually region-bound) or via **filesystem backup** (Kopia/Restic, slower, but portable across providers and storage classes, and works for volume types with no snapshot support).

*Excludes*, and this is the important half:

- **Data not on a PV** - anything in `emptyDir`, in the container's writable layer, or in memory.
- **The consistency of the application's data.** A volume snapshot of a running database is a crash-consistent copy, not a transactionally consistent one. Velero's **backup hooks** (`pre` and `post` exec hooks to quiesce and unquiesce) exist for this and are frequently not configured, so people have backups that require crash recovery on restore and may not be restorable at all.
- **Multi-volume consistency.** Volumes are snapshotted independently, so a system spanning several volumes has no consistent point.
- **The managed services** the applications depend on - the RDS instance, the S3 bucket, the Kafka topic. Velero has no idea they exist, and a restored cluster pointing at a database that was also lost is worthless.
- **etcd**, unless you back it up separately (`etcdctl snapshot save`, or the managed provider's own mechanism - on EKS the control plane is AWS's responsibility, which removes this concern).
- **Cluster-level cloud configuration** - the node groups, IAM roles, load balancers, DNS. That is Terraform's job.
- **Secrets, in a usable form** - a Velero backup contains Secret objects, which means it contains every credential in plaintext-equivalent form. That backup is now a top-tier secret itself, which people routinely fail to account for.

**The strategy I would run**: managed services backed up and restore-tested by their own native mechanisms (the priority); the cluster itself treated as **rebuildable rather than restorable** - Terraform plus GitOps recreates it from nothing, which is a better guarantee than a backup and is exercised continuously; Velero for the genuinely stateful in-cluster workloads with properly configured quiesce hooks, replicated cross-region; and a periodic **full rebuild drill** (Q225) proving the cluster can be recreated and the data reattached.

### Q227. DR patterns

| Pattern | What is running | Typical RTO | Typical RPO | Relative cost |
| --- | --- | --- | --- | --- |
| **Backup and restore** | Nothing. Backups in another region. | **Hours to days** | Hours (last backup) | ~5% of primary - storage only |
| **Pilot light** | Data replicated continuously; core infrastructure defined but scaled to zero or minimal | **Tens of minutes to hours** | Minutes | ~15-25% - replication plus minimal always-on |
| **Warm standby** | A scaled-down but *running* copy of the whole stack, continuously replicated | **Minutes** | Seconds to minutes | ~30-50% |
| **Active-active** | Full capacity in both regions, both serving | **Near zero** - traffic shifting, not failover | Near zero (or a consistency trade-off) | **>200%** - each region must carry full load alone |

**How I choose**, in order:

1. **Start from the business impact of downtime and of data loss**, quantified - revenue per hour, regulatory exposure, contractual penalties, reputational cost. Without a number, the conversation is about feelings and the answer is always "active-active" until the invoice arrives.
2. **Derive RTO and RPO from that**, separately (Q224). They frequently differ - "we can be down for two hours but must not lose a single payment" is common and points at pilot light with synchronous data replication.
3. **Pick the cheapest pattern that meets both.** They are a ladder, and the cost step from warm standby to active-active is the steepest on it.
4. **Segment by tier.** Not everything needs the same pattern. Active-active for the payment path, warm standby for the core application, backup-and-restore for the reporting stack and internal tools. Applying one pattern to the whole estate is how DR budgets get rejected.
5. **Weigh operational cost, not just infrastructure cost.** Active-active means every change is a multi-region change, data consistency is a permanent design constraint (Q228), and the complexity is paid every day rather than during a disaster. That ongoing cost is usually larger than the infrastructure bill and is almost always omitted from the comparison.
6. **Prefer the pattern you will actually rehearse.** A warm standby tested quarterly beats an active-active configuration nobody has failed over.

A point worth making: **active-active is not a DR pattern**, it is an architecture. It gives you disaster resilience as a side effect of always running in two places, which is why it works - there is no untested failover path.

### Q228. Multi-region failover

Beyond replication, four things:

**1. DNS and traffic steering.** Failover means changing where clients go, and DNS is a poor mechanism for it: TTLs are advisory (resolvers, ISPs, browsers and the JVM all cache beyond them - Q105), negative caching extends the window, and a 60-second TTL routinely means 5-15 minutes of real-world propagation. Health-check-driven Route 53 failover helps; **anycast or a global load balancer** (CloudFront, Global Accelerator, Cloudflare) is much better because the change happens in the network rather than in every client's cache. Long-lived connections do not re-resolve at all and must be actively closed.

**2. State, which is the hard part.**

- **Asynchronous replication means the standby is behind**, so failing over loses the replication lag - that is your real RPO, and it is unbounded during exactly the incident that causes failover (a saturated primary replicates more slowly).
- **Failing back is harder than failing over.** The new primary has accepted writes the old one never saw; reconciling them is a data problem with no generic solution.
- **Split brain**: if the old primary is not truly dead, you have two writable primaries diverging. Fencing (STONITH, a lease, disabling the old primary's network) is mandatory and frequently absent.
- **Non-database state** is routinely forgotten: object storage replication lag, cache contents, in-flight messages in a queue, sticky sessions, scheduled job leadership, and idempotency keys.

**3. Quorum and the coordination layer.** Anything consensus-based - etcd, ZooKeeper, Kafka's controller, a distributed lock - needs a **majority**, so two regions cannot form a quorum that survives losing one. You need three failure domains (a third region, or a witness), or you accept that the minority side is read-only. Two-region active-active with a quorum-based coordinator is a design that looks correct and cannot survive the failure it exists for.

**4. The decision to fail over - the genuinely hardest part.**

- **Detection is ambiguous.** Is the region down, or is monitoring partitioned from it? A network partition looks identical to a failure from one side, and failing over on a monitoring outage causes the incident.
- **Failover is itself high-risk.** It exercises a rarely-used path, loses data, and may not work (Q229). So the decision is "accept a known outage" versus "take a risky action with an uncertain outcome", under time pressure with incomplete information.
- **Therefore it needs a pre-agreed policy**: who decides (a named role, not a committee), on what criteria (specific, measurable thresholds sustained for a specific duration), and with what authority. Deciding the criteria during the incident is how a 20-minute outage becomes two hours.
- **Automatic failover** removes the hesitation and adds the risk of failing over spuriously. For most systems I would automate the *detection and preparation* and keep a human on the trigger, with the decision criteria written down in advance.

### Q229. Drill worked, real failover failed `[T]`

1. **The drill was scheduled; the disaster was not.** In the drill the system was healthy, traffic was low, no deployment was in flight, no other incident was in progress, and the standby had had a quiet night to catch up on replication. In the real event the primary was saturated - which is *why* it failed - so replication lag was large, connections were exhausted, and the standby was further behind than it had ever been in a drill.
2. **The drill was graceful; the failure was not.** A drill fails over cleanly: the primary is quiesced, connections drained, replication allowed to catch up, then the switch. A real failure is abrupt and partial - the primary is *half* alive, still holding locks, still accepting some connections, still writing. That is the split-brain and fencing problem (Q228), and it does not exist in a drill where you politely shut things down.
3. **The people were different.** The drill was run by the team that built it, in working hours, with everyone available and the runbook open on a second screen. The real event was at 03:00, run by whoever was on call, possibly someone who has never done it, while also handling customer escalations and a stakeholder call. Every step that relies on tacit knowledge fails here.
4. **Scope was narrower in the drill.** A drill fails over *one* system - the database, or the application tier. A real regional event takes out everything simultaneously, including things the drill assumed were available: the CI system used to deploy the standby, the secrets store, the observability stack, the DNS automation, the identity provider, and the chat tool you were coordinating in. **Dependencies of the failover procedure** are the classic missed category.
5. **Drift since the drill.** Six months of changes - new services, new dependencies, a changed schema, a new secret, an IAM policy that only exists in the primary region, a resource created by hand. The standby was correct in March and is not in September, and nothing detected it.
6. **The drill validated the mechanism, not the capacity.** The standby was scaled small for cost, and scaling it up under real load hit an instance quota, a subnet IP exhaustion, or a cold cache that made it fall over at a fraction of the primary's throughput.

**What narrows the gap**: fail over **regularly and for real** - run production from the secondary region for a week each quarter, so the standby is continuously proven and drift cannot accumulate; make failover **the routine path, not the exceptional one**; run drills unannounced, out of hours, with the on-call responder rather than the designers; and explicitly enumerate and test the **dependencies of the failover procedure itself**.

### Q230. Graceful degradation as the default

**What a service does when a non-critical dependency is down**: it serves a **reduced but coherent** response rather than an error. Concretely, in order of preference:

1. **Serve stale.** A cached value past its TTL is almost always better than an error - "stale-while-revalidate" as a standing policy rather than an exception.
2. **Serve a static or computed fallback** - a default recommendation set, an empty-but-explicit section, a generic message.
3. **Omit the feature** and return the rest, with the response indicating the omission so the client can render sensibly.
4. **Queue the work** for later, if it is a write that need not be synchronous.
5. **Fail the request**, only if the dependency is genuinely required for correctness.

The critical constraint from `03-microservices` Q115: **a fallback must not be silently wrong**. Returning an empty list where the real answer is "3 items in your basket" is worse than an error, because the user acts on it. The rule is that a fallback must be either *obviously degraded* to the caller, or *safe to act on*. Degradation must be visible - to the user in the UI, and to you as a metric.

**Making it the default rather than an afterthought:**

1. **Classify every dependency at design time** as critical or non-critical, and record it. That single act forces the conversation, and the answer is usually that far fewer dependencies are critical than the code implies.
2. **Make the framework fail safe.** A shared client library where the default configuration is a bounded timeout, a circuit breaker and a required fallback - and where *not* supplying a fallback for a non-critical dependency is a compile-time or review-time failure. Defaults determine behaviour far more reliably than guidelines.
3. **Timeouts on everything, always**, derived from the caller's budget (`03-microservices` Q102-104). An unbounded call is a dependency that can take you down regardless of how critical it is.
4. **Make degradation a first-class, observable state**: a metric per feature (`feature_degraded{feature="recommendations"}`), surfaced on the dashboard, so "we are running degraded" is a known condition rather than a discovery.
5. **Test it continuously** - game days (Q223) that take each non-critical dependency down and verify the service stays within its steady state. A fallback that is never exercised does not work; this is the mechanism that keeps it honest.
6. **Give the product owner the decision.** "When recommendations are unavailable, do we show nothing, show popular items, or show an error?" is a product question, and asking it once per feature is what turns degradation from an engineering afterthought into a designed behaviour.

### Q231. The business asks for 99.99 percent `[A]`

**Do not say no, and do not say yes.** Find out what they actually mean, then price it.

**The conversation:**

1. **"What are we protecting against?"** Almost always the request comes from a specific painful memory - an outage that cost a deal, a customer escalation, an SLA penalty - or from a competitor's marketing number. Understanding the driver often reveals that the real requirement is something else: "we must never lose an order", or "the January peak must not fail", or "our largest customer must not be affected".
2. **"99.99 percent of what, measured where, over what window?"** (Q198.) Four nines on the checkout path is a completely different proposition from four nines on the whole product including reporting and admin. Scoping the SLO to the user journey that matters is usually where most of the cost disappears.
3. **"What does an hour of downtime actually cost?"** Get a number. This is what makes the rest of the conversation quantitative rather than aspirational, and it very often turns out that the cost of downtime is far lower than the cost of preventing it.
4. **Explain the operational meaning, not the arithmetic**: 99.99 percent is **4.3 minutes a month** (Q216). That is less time than it takes to wake up, read a page and open a laptop. So it does not mean "try harder" - it means **no incident may require a human**, which is an architectural constraint, not an effort level.

**What it would cost - presented as a concrete bill:**

- Multi-region active-active (Q227): **more than double** the infrastructure, plus a permanent data-consistency constraint on every feature built from now on.
- Every dependency must also be at four nines or be made optional (Q217). This includes third parties you do not control, which is often where the requirement becomes literally unachievable and the conversation becomes honest.
- Automated detection and remediation for every failure mode, which is a substantial and ongoing engineering investment.
- Progressive delivery with automated abort on every release (Q137), because deployments would otherwise consume the entire budget.
- No maintenance windows, ever.
- Roughly 20-30 percent of engineering capacity redirected from features to reliability, permanently. **This is the cost that actually matters and the one nobody mentions.**

**What I would commit to:**

- **A tiered SLO**: 99.99 percent on the narrow critical path (checkout, payment, authentication) if the numbers justify it, **99.9 percent on the main application**, and lower on everything else. This is almost always the right answer, because it concentrates spend where the money is.
- **An SLA looser than the SLO**, so there is room between "we are unhappy" and "we owe you money".
- **A staged plan**: reach and hold 99.9 percent reliably for two quarters first. An organization that cannot consistently hit three nines will not hit four by being asked to, and the work to hit three - error budgets, progressive delivery, automated rollback, alert hygiene - is the same work that makes four possible later.
- **An error budget policy** with real consequences, so the target is a shared constraint on how we work rather than a number in a slide.

**What I would refuse**: committing to a number I have not measured, committing before the dependencies have been assessed, or accepting a target with no accompanying change to how the organization prioritizes. A four-nines commitment with a feature roadmap unchanged is a promise to fail publicly in nine months.

*Hook: an availability conversation with a business stakeholder, and the number you actually committed to.*

---

## 15. Pipeline and runtime security

### Q232. Shift-left security

**In pipeline terms**: move security checks from a pre-release audit into the development loop - secret scanning at commit, dependency and static analysis on the pull request, image scanning at build, policy checks on the manifest - so that a defect is found by the person who introduced it, minutes after they introduced it, when fixing it is cheap.

The economics are the argument: a finding at commit costs minutes; the same finding in a pre-release penetration test costs a release slip and a context switch; in production it costs an incident.

**The failure mode of taking it too literally**: piling every check into the pull request until the pipeline is a wall of findings.

- **Signal-to-noise collapses.** A SAST tool with a 40 percent false-positive rate, run on every PR as a blocking gate, produces a team that clicks "suppress" reflexively. You have trained people to ignore security findings, which is worse than not running the tool.
- **Latency.** A full DAST scan or a deep SCA analysis on every commit adds tens of minutes to the feedback loop, which is the thing shift-left was supposed to protect (Q3).
- **Responsibility gets pushed without capability.** "Developers own security now" without training, without tooling that explains findings, and without a security team to escalate to, is abdication rather than delegation.
- **It only covers what a scanner can see.** Shift-left is very good at known vulnerable patterns and known vulnerable dependencies. It is nearly useless for design flaws, authorization logic, business-logic abuse and multi-service attack paths - and an organization that believes the pipeline covers security stops doing threat modelling and design review, which is where the serious findings actually come from.
- **Runtime is still required.** Nothing at build time tells you what is actually running or what it is doing (Q243).

The correct position: shift left **what is cheap, fast and precise**; keep the slow and imprecise checks asynchronous; and keep the human activities - threat modelling, design review, penetration testing - because they find a different class of problem.

### Q233. Secret scanning at three stages

| Stage | Catches | Why the others do not |
| --- | --- | --- |
| **Pre-commit** (client-side hook, `gitleaks`, `talisman`) | The secret **before it enters history**, which is the only point at which cleanup is genuinely free | Can be bypassed (`--no-verify`), is not installed on every machine, and does not exist for changes made through the web UI or by automation. It is a convenience, not a control. |
| **Server-side push protection** | The secret **before it reaches the remote**, un-bypassably | This is the real control, because it cannot be skipped locally. But it only sees new pushes - it is blind to everything already in the repository. |
| **Historical scanning** | Secrets **already committed**, possibly years ago, in any branch, in deleted files, in commits no branch points at | The other two are prospective only. The first time you scan history you find things, always. |

**Why you need all three**: they cover different time domains. Pre-commit protects the developer's flow; push protection is the enforceable boundary; historical scanning covers the debt that already exists and the secrets that were committed before any of this was turned on. Remove any one and there is a class of leak you never see.

Two additions worth naming:

- **Scan more than git**: CI logs, container image layers (a secret baked into an image is not in git), Terraform state files, and issue trackers.
- **Validate the finding.** Modern scanners can test whether a detected credential is *live*, which is what separates 400 findings from the 6 that matter and is what makes triage tractable.
- **Detection must be wired to automatic revocation** where possible - GitHub's partner program revokes leaked cloud keys automatically. Detection without revocation is Q126 with a shorter delay.

### Q234. OIDC federation from GitHub Actions to AWS

**The exchange:**

1. GitHub Actions runs an OIDC identity provider at `token.actions.githubusercontent.com` with a published JWKS.
2. That provider is registered in AWS IAM as an **OIDC identity provider**, and an IAM role's trust policy allows `sts:AssumeRoleWithWebIdentity` for it, with conditions on the token's claims.
3. In the workflow, `permissions: id-token: write` allows the job to request a token. The `aws-actions/configure-aws-credentials` action calls GitHub's token endpoint (using `ACTIONS_ID_TOKEN_REQUEST_URL` and `..._TOKEN`, which are injected only into that job) and receives a **short-lived JWT** signed by GitHub, containing claims: `iss`, `aud`, `sub` (e.g. `repo:org/service:ref:refs/heads/main`, or `repo:org/service:environment:production`), `repository`, `repository_owner`, `job_workflow_ref`, `workflow`, `ref`, `sha`, `event_name`, `runner_environment`.
4. The action calls **`sts:AssumeRoleWithWebIdentity`** with that JWT.
5. **STS validates it**: fetches GitHub's JWKS via the registered provider, verifies the signature, checks `iss`, `aud` and expiry, then evaluates the role's trust policy conditions against the claims.
6. STS returns **temporary credentials** valid for the session duration (up to an hour), which the SDK uses.

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::123:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:myorg/orders:environment:production"
    }
  }
}
```

**Why this beats a stored access key:**

- **Nothing long-lived exists.** There is no secret to leak, rotate, or find in a log. A key in GitHub Secrets is a permanent credential that is one misconfiguration away from exfiltration (Q235).
- **Credentials are short-lived and scoped to one job run.**
- **The identity is rich and enforceable.** The trust policy can require a specific repository, a specific branch, a specific environment, or a specific reusable workflow - so a compromise of one repository does not grant another's role.
- **Revocation is a policy edit**, not a rotation across N consumers.
- **No rotation burden**, which means it actually stays correct.

**The condition that must not be got wrong**: pin `sub` as precisely as possible. `"StringLike": {"...:sub": "repo:myorg/*"}` grants every repository in the org; omitting the `sub` condition entirely grants **every GitHub repository in the world**, which is a real and repeatedly-observed misconfiguration.

### Q235. OIDC and pull_request_target `[T]`

**The vulnerability**: `pull_request_target` runs the workflow **in the context of the base repository** rather than the fork - with the base repository's secrets available, with a read-write `GITHUB_TOKEN`, and with permission to request an OIDC token. Critically, it runs the workflow definition from the **base branch**, which is why it feels safe: an attacker cannot modify the workflow file.

But the workflow's *contents* are not the only attacker-controlled input. The attack is:

1. An attacker opens a pull request from a fork against your repository. They do not need any permissions; anyone can open a PR.
2. The `pull_request_target` workflow triggers, in the base repository's privileged context.
3. The workflow does something that **executes code from the pull request**. The classic is an explicit checkout of the PR head:

```yaml
on: pull_request_target
jobs:
  build:
    permissions: { id-token: write, contents: read }
    steps:
      - uses: actions/checkout@v4
        with: { ref: ${{ github.event.pull_request.head.sha }} }   # attacker's code
      - uses: aws-actions/configure-aws-credentials@v4
        with: { role-to-assume: arn:aws:iam::123:role/prod-deploy }
      - run: npm ci && npm run build     # runs the attacker's package.json scripts
```

But it does not require an explicit checkout. **Any** execution of fork-controlled content does it: running `mvn`/`npm` against the PR's build files, a build script, a Makefile, a linter with a config file, or even interpolating `${{ github.event.pull_request.title }}` into a `run:` block (script injection).

4. The attacker's code now runs **with the ability to request an OIDC token and assume the production role**. It calls `configure-aws-credentials` itself, or simply reads the credentials the workflow already configured from the environment, or exfiltrates the OIDC token to a remote endpoint and assumes the role from anywhere.

The result is **production access from an unauthenticated, unreviewed pull request opened by anyone on the internet**. It requires no approval, because `pull_request_target` deliberately bypasses the first-time-contributor approval gate that `pull_request` has.

**The defences**: never check out or execute untrusted code in a `pull_request_target` workflow (use it only for things needing no fork content, like labelling); use `pull_request` for anything that builds fork code, accepting that it has no secrets; put the OIDC role behind a **GitHub Environment with required reviewers**, and scope the trust policy's `sub` to `environment:production` so a token from a PR context cannot assume it (this is the control that makes the mistake survivable); and never interpolate event data directly into shell commands.

### Q236. Least privilege for a CI pipeline

**What a deploy job actually needs** - and it is much less than teams grant:

- **To push an image**: `ecr:GetAuthorizationToken` (account-level), plus `ecr:BatchCheckLayerAvailability`, `InitiateLayerUpload`, `UploadLayerPart`, `CompleteLayerUpload`, `PutImage` **on the one repository**. Not `ecr:*`, and specifically not `ecr:DeleteRepository` or `BatchDeleteImage`.
- **To deploy via GitOps**: write access to *one directory* of *one repository*. That is the entire permission set, and it is the strongest argument for GitOps (Q150) - the deploy credential is a git token, not a cloud role.
- **To deploy directly to Kubernetes**: a ServiceAccount with a Role (namespaced, not ClusterRole) granting `get/list/watch/create/update/patch` on the specific resource kinds in one namespace. Not `delete` on everything, not cluster-scoped, not `secrets` unless genuinely required.
- **To read a parameter or secret**: `ssm:GetParameter` on a specific path prefix.
- **To run a migration**: network access and a database credential scoped to DDL on one schema.

Everything else - reading the repository, uploading artifacts - is the `GITHUB_TOKEN`, which should be `permissions: contents: read` at the workflow level with individual jobs elevating only what they need.

**Scoping per environment:**

1. **One IAM role per service per environment.** Never a shared "ci-deploy" role. The blast radius of a compromise is then one service in one environment.
2. **The trust policy pins the identity precisely** (Q234): repository, and `environment:production` rather than a branch, because environments carry protection rules.
3. **GitHub Environments with required reviewers and branch restrictions** guard the production role, so obtaining the token requires an approval that the workflow itself cannot grant.
4. **Separate jobs for separate privilege levels.** The job that builds untrusted code has no `id-token: write`; the job that deploys does nothing but deploy. Since the job is the isolation boundary (Q31), this is the mechanism that makes it real.
5. **Different accounts per environment**, so a production role cannot exist in the non-production account at all.
6. **Session tagging and CloudTrail** so every action is attributable to a workflow run and a commit.

### Q237. Third-party GitHub Actions

**The risk**: `uses: some-org/some-action@v1` executes arbitrary code **inside your job**, with your job's filesystem, environment, secrets and `GITHUB_TOKEN`. It is a runtime dependency with full privilege and no sandbox, and `@v1` is a **mutable tag** that the author can re-point at any time - including after you have reviewed it. A compromised or malicious maintainer changes the tag and every consumer executes the new code on the next run, with no diff and no notification. This is exactly the `tj-actions/changed-files` pattern that has occurred in the wild.

**Policy:**

1. **Pin to a full commit SHA**, always: `uses: actions/checkout@8f4b7f8...` with a comment naming the version. This is the single control that matters, because a SHA is immutable - a compromised tag cannot affect you. Dependabot and Renovate both understand SHA pinning and will raise update PRs, so the ergonomic cost is low.
2. **Allow-list at the organization level.** GitHub's Actions policy can restrict to actions created by GitHub, by verified creators, or to an explicit list. Default-deny with an explicit allow-list is the enforceable version of policy 1.
3. **Vet before adding**: is it maintained, how many maintainers, is the source readable, does it need the permissions it asks for, does it make network calls, is there a verified publisher badge. For anything touching secrets or credentials, read the source.
4. **Prefer fewer actions.** A `run: curl ...` or three lines of shell is often safer than an action, because it is reviewable in the diff. Many popular actions are wrappers around one command.
5. **Vendor the critical ones** - fork into the organization and consume from there, so a change requires a PR in your own repository. Reserve this for actions that touch credentials, because it creates a maintenance obligation.
6. **Structural containment**: minimum `permissions` per job, no secrets in jobs that use third-party actions where avoidable, OIDC rather than stored keys (so there is no long-lived credential to steal), and separate jobs for privileged operations.
7. **Monitor egress** from runners where the environment allows it, and alert on unexpected destinations.

### Q238. Image scanning at three points

| Point | Catches | Misses |
| --- | --- | --- |
| **In the pipeline** (at build) | Vulnerabilities in the image you just built, **before it ships**, with the fastest and cheapest feedback loop and a natural owner | Only scans at a moment in time. A CVE published tomorrow against an image built today is invisible - and most vulnerabilities in a running image were disclosed *after* it was built. |
| **In the registry** (continuous rescan) | **Newly disclosed CVEs against images already built**, including images running in production right now. Also scans images that arrived by other routes - pushed by hand, pulled from a vendor | Tells you an image is vulnerable; does not stop it running, and does not tell you *where* it is running unless you correlate |
| **At admission** (in the cluster) | The **last gate**: refuses to run an image that fails policy, regardless of how it got there. Enforces signature and provenance too (Q60) | Blind to anything already running, and it is a blunt instrument - blocking a deploy during an incident because of a medium CVE is how admission policies get disabled |

**Why all three, in one line each**: the pipeline gives you cheap feedback and prevention, the registry gives you *time-based* coverage the pipeline structurally cannot have, and admission gives you *enforcement* the other two cannot.

The one people skip is the registry rescan, and it is the one that answers the question that actually gets asked during an incident: "which of our running images contain this CVE?" Answering that requires continuous rescanning correlated with a deployment inventory, and it is why the SBOM (Q48) is attached to the digest.

The practical configuration: pipeline scan fails only on **critical, fixable, reachable** findings; registry rescan raises tickets with an SLA by severity; admission enforces signature and provenance always, and CVE policy in **audit mode first**, moving to enforce only for the highest severities once the estate is clean enough that it will not block an emergency fix.

### Q239. Admission control

**Validating versus mutating webhooks**: the API server calls **mutating** webhooks first (they may patch the object - sidecar injection, defaulting, adding labels), then runs schema validation and object validation, then calls **validating** webhooks (accept or reject, no modification). Both are configured with rules matching resources and operations, and both have a `failurePolicy` (`Fail` or `Ignore`) that decides what happens when the webhook is unreachable - `Fail` is correct for security policy and means **your webhook is now a cluster availability dependency**, which is the operational trade-off to name.

| | Model |
| --- | --- |
| **Pod Security Admission** | Built in, no webhook. Applies one of three **predefined** profiles - `privileged`, `baseline`, `restricted` - per namespace via labels, in `enforce`, `audit` or `warn` mode. Zero operational cost, zero flexibility. Replaced PodSecurityPolicy. |
| **OPA Gatekeeper** | Rego policies packaged as `ConstraintTemplate` + `Constraint`. Extremely expressive, general-purpose, with an audit mode that reports existing violations. Cost: Rego is a real learning curve and the resource model is verbose. |
| **Kyverno** | Policies written in **YAML** rather than a policy language, Kubernetes-native. Can validate, **mutate**, **generate** (create a default NetworkPolicy in every new namespace), and **verify image signatures** natively. Much lower barrier; slightly less expressive at the extremes. |

**What I enforce by default:**

1. **Pod Security Admission at `restricted`** in every application namespace, with `baseline` as the transitional step and named exemptions for system namespaces. This is free and covers most of Q240.
2. **Image provenance**: images must come from our registry, must be referenced **by digest**, and must have a valid signature whose identity matches an expected workflow (Q60). Kyverno does this natively.
3. **Resource requests and limits present** on every container (memory limit mandatory; CPU limit per Q93), and a `LimitRange` providing defaults.
4. **No `latest` tag, no `imagePullPolicy: Never`.**
5. **Required labels** for ownership and cost attribution (`team`, `service`, `environment`) - unglamorous and it makes Q250 possible.
6. **PodDisruptionBudget present** for anything with more than one replica, and **not** one that makes a drain impossible (Q116).
7. **Default-deny NetworkPolicy generated** in every namespace (Kyverno `generate`).
8. **No `hostNetwork`, `hostPID`, `hostPath`, or privileged containers** outside an explicit exemption list.

Rolled out in **audit mode first**, with the violation inventory published and a ratchet, exactly as in Q175 - turning on enforcement against a non-compliant estate gets the policy engine removed.

### Q240. Pod security settings and Java

```yaml
securityContext:            # pod level
  runAsNonRoot: true
  runAsUser: 10001
  fsGroup: 10001
  seccompProfile: { type: RuntimeDefault }
containers:
  - securityContext:        # container level
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: { drop: ["ALL"] }
```

**What breaks a typical Java service, and the fix:**

| Setting | Breakage | Fix |
| --- | --- | --- |
| `runAsNonRoot` | The image's `USER` is root, or is not set, so the kubelet refuses to start it. Also: files copied in during the build are owned by root and unreadable by the runtime UID | Set `USER` in the Dockerfile, and `COPY --chown`. Use a numeric UID, because `runAsNonRoot` validation cannot resolve a username |
| **`readOnlyRootFilesystem`** | **The most common breakage.** The JVM writes to `/tmp` - hsperfdata for `jcmd`/`jps`, temporary files, extracted native libraries from JARs (Netty, SQLite, snappy), Tomcat's work directory, and heap dumps | Mount an `emptyDir` at `/tmp` (and at Tomcat's work dir), set `-Djava.io.tmpdir=/tmp`, and `-XX:HeapDumpPath` to a writable volume. This is nearly always sufficient |
| `capabilities: drop ALL` | Binding to a port below 1024 fails without `NET_BIND_SERVICE` | Never bind below 1024 in a container - use 8080. There is no reason to need the capability |
| `allowPrivilegeEscalation: false` | Rarely breaks a JVM. Occasionally breaks an agent or an init script using `sudo` or a setuid binary | Remove the agent's need for it |
| `seccompProfile: RuntimeDefault` | Very rarely an issue; some JVM native operations and some profilers (`perf`-based, async-profiler needing `perf_event_open`) are blocked | Use a custom profile for the profiling case, or run the profiler in an ephemeral debug container |
| `fsGroup` | A mounted PV owned by root is unwritable | Set `fsGroup`; note it triggers a recursive `chown` on the volume, which is slow for large volumes (`fsGroupChangePolicy: OnRootMismatch` mitigates) |

The general point worth making: **almost all of these are cheap and are blocked by one thing - `/tmp`.** An organization can move its whole Java estate to `restricted` Pod Security with a base image that sets a non-root UID and a `/tmp` `emptyDir` in the shared deployment template. That is a platform change, not 40 team changes, which is what makes it achievable.

### Q241. A container running as root `[T]`

**Root inside the container, with no user namespace, means UID 0 on the host kernel** - the isolation comes from namespaces, cgroups, capabilities and seccomp, not from the UID. So what it can do is bounded by the capability set, not by the fact that it is "in a container".

**With a default runtime capability set** (Docker/containerd defaults, which Kubernetes inherits unless you drop them):

- Install packages, modify any file in the container, replace binaries on the `PATH`.
- `CAP_NET_RAW` (default) - **craft raw packets**, enabling ARP spoofing and DNS spoofing against other pods on the node. This is why dropping `NET_RAW` matters even when nothing else is granted.
- `CAP_CHOWN`, `DAC_OVERRIDE`, `SETUID`, `SETGID`, `FOWNER` - full control of the container's filesystem regardless of permissions.
- Read the pod's ServiceAccount token and every mounted secret - though a non-root user can do that too.
- Exploit any kernel vulnerability from a position of higher privilege than a non-root user would have. Container escapes overwhelmingly require root in the container as a precondition.

**What changes with `hostPID`:**

- The container sees **every process on the node**. `/proc/<pid>/environ` for other processes exposes **their environment variables**, which is where other pods' secrets live if they use env vars (Q120). `/proc/<pid>/root` gives access to other containers' filesystems. `/proc/<pid>/cwd`, open file descriptors, and command lines are all readable.
- It can **signal and kill** processes on the host, including the kubelet.
- Combined with `CAP_SYS_PTRACE`, it can attach to and inject code into any process on the node.
- The classic escape: `nsenter --target 1 --mount --uts --ipc --net --pid -- bash` gives a root shell in the host's namespaces.

**What changes with a `hostPath` mount:**

- `hostPath: /` or `/etc` - read every secret on the node, modify host configuration, write an SSH key into `root/.ssh/authorized_keys`, or drop a static pod manifest into `/etc/kubernetes/manifests` which the kubelet will run **as a privileged pod**.
- `hostPath: /var/run/docker.sock` or the containerd socket - **this is root on the host, immediately**. Launch a privileged container mounting the host root filesystem.
- `hostPath: /var/lib/kubelet` - read the kubelet's credentials and every secret mounted for every pod on the node.
- `hostPath` on any device node with `CAP_MKNOD` or `SYS_ADMIN` - mount the host's disk directly.

The summary for an interview: **root in a container is a bad idea; root plus `hostPID`, `hostPath` or a privileged flag is not containment at all** - it is a process on the node with a different filesystem view. Those three are what admission control exists to block.

### Q242. Kubernetes RBAC

**Role versus ClusterRole**: a `Role` grants permissions on namespaced resources **within one namespace**; a `ClusterRole` defines permissions that are either cluster-scoped (nodes, PVs, namespaces, CRDs) or reusable across namespaces. A `ClusterRole` bound with a `RoleBinding` grants its permissions **only in that namespace** - which is the idiomatic way to define a permission set once and grant it per namespace. Bound with a `ClusterRoleBinding`, it grants cluster-wide.

**Verbs that are effectively cluster admin:**

- **`escalate`** on roles - explicitly lets you grant yourself permissions you do not have. It exists to bypass the privilege-escalation prevention, and granting it is granting everything.
- **`bind`** on rolebindings/clusterrolebindings - lets you bind `cluster-admin` to yourself.
- **`impersonate`** on users/groups/serviceaccounts - become anyone, including `system:masters`. Total.
- **`create` on pods** in any namespace - you can mount any ServiceAccount in that namespace, mount `hostPath`, set `privileged: true` and escape to the node (Q241). **Pod creation is node-level compromise** unless admission control prevents it, which is why Q239 is not optional.
- **`get`/`list` on secrets** - reads every credential in scope, including ServiceAccount tokens, which you can then use.
- **`create` on serviceaccounts/token** - mint a token for any ServiceAccount in the namespace.
- **`create`/`update` on validatingwebhookconfigurations or mutatingwebhookconfigurations** - intercept and rewrite every API request in the cluster.
- **`update`/`patch` on nodes** - manipulate scheduling; combined with pod creation, place a workload wherever you want.
- **`*` on `*`** and any wildcard `apiGroups: ["*"]`, obviously.
- **`create` on pods/exec and pods/portforward** - exec into any pod in scope, so you inherit whatever that pod can do.

**What I never grant**: `escalate`, `bind`, `impersonate`, wildcards on resources or verbs, `ClusterRoleBinding` to anything with secret or pod-create permissions, and `cluster-admin` to a human as a standing grant (break-glass only, time-bounded and alerted). I also treat **`create pods`** as a privileged grant that must be paired with restrictive Pod Security Admission, because most people do not realize it is one.

### Q243. eBPF runtime security

Image scanning answers "what is in this artifact"; runtime detection answers "what is this process actually doing". eBPF programs attached to kernel tracepoints, kprobes and LSM hooks see syscalls, process execution, file access, network connections and privilege changes, in-kernel, with low overhead and without modifying the application.

**What it sees that scanning cannot:**

1. **Execution of something that was never in the image** - a binary downloaded at runtime, an interpreter running fetched code, a webshell. The image was clean; the container is not (Q61).
2. **Exploitation of a vulnerability**, as opposed to its presence. A scanner says a CVE exists; runtime detection sees the shell spawned by the exploit. Most CVEs are never exploited, and the ones that are produce a very distinctive runtime signal.
3. **Zero-days and logic abuse**, which have no CVE and therefore no scanner signature at all.
4. **Behaviour that is not a vulnerability**: a process reading `/var/run/secrets/kubernetes.io/serviceaccount/token`, an outbound connection to an unexpected destination, a container writing to `/etc`, a `setuid` call, an unexpected `execve` of `sh` in a distrolesss container.
5. **Container escape attempts** - `nsenter`, mounting the docker socket, writing to `/proc/sys`, loading a kernel module.
6. **Lateral movement and data egress**, which are network behaviours no build-time tool can model.
7. **What is *actually* loaded and used** - Cilium and Tetragon can report which packages and code paths are exercised, which feeds directly into the reachability triage of Q56.

**The trade-offs**: it produces alerts requiring triage and tuning (a fresh Falco install is very noisy against a real estate); rules are behavioural, so false positives are inherent; a node-level agent with kernel access is itself a privileged component and a supply-chain concern; and it needs a modern kernel. Tetragon's advantage over classic Falco is that it can **enforce** (kill the process, block the syscall) in-kernel rather than only alerting - which turns detection into prevention but raises the stakes on false positives considerably.

### Q244. Audit logging

**Kubernetes**: the API server's audit log records every request - who (user, group, service account), what (verb, resource, namespace, name), when, from where (source IP, user agent), the response code, and - depending on the configured level - the request and response bodies. The **audit policy** sets the level per resource: `None`, `Metadata`, `Request`, `RequestResponse`. The practical configuration: `Metadata` for most things, `RequestResponse` for RBAC changes and admission configuration, and **`None` for secrets' request bodies** (or you have written every secret into the log). Shipped off-cluster immediately, because a log stored where the attacker is has limited value.

**CI**: workflow runs with the triggering identity and event, every job's logs, secret access, environment approvals, changes to workflow files, changes to organization and repository settings, changes to secrets, and every OIDC token issuance and role assumption (the latter in CloudTrail).

**What I retain**: the compliance-mandated window for regulated systems (often 1-7 years, in immutable storage); operationally, 90 days hot and a year cold covers virtually every real investigation. CI logs are the ones people under-retain - GitHub's default retention is 90 days and it is adjustable, and a supply-chain investigation frequently needs to go back further.

**The question the log must be able to answer**, and this is the design criterion:

> **"Who or what caused this specific change to this specific resource, when, from where, and through which pipeline and commit?"**

That is one question, and answering it requires the logs to be **joinable**. Concretely: the deployment must record the commit SHA; the CI run must record the identity and the OIDC session; the assumed role session must be tagged with the workflow run ID so CloudTrail entries carry it; and the Kubernetes audit entry must show which ServiceAccount or federated identity made the change. If any link is missing, you can see that something happened and not what caused it - which is the state most estates are actually in.

The secondary question is the security one: **"what did this identity do, everywhere, in this time window?"** - which requires the audit logs to be centralized and correlatable across the cluster, the cloud and the CI system.

### Q245. Compromised build agent `[T]`

**What they have, assuming an ordinary setup:**

1. **Every secret configured for the jobs that run on it** - registry credentials, cloud keys, signing keys, database credentials, API tokens. On a shared or non-ephemeral agent, that means every secret from every job it has ever run, if any were written to disk or remain in a credential cache (Q33).
2. **The ability to modify build outputs.** They do not need to touch your source at all - they alter the artifact after compilation, or poison the dependency cache so future builds are compromised. This is the most dangerous capability, because the result is a **signed, provenance-attested, correctly-deployed backdoor**, and every downstream control (signature verification, admission) validates it.
3. **Deployment access**, if the agent deploys - a kubeconfig, an assumed cloud role, or write access to the GitOps repository. In a push-based pipeline this is direct production access.
4. **Source code**, and write access to it if the agent has a token that can push.
5. **Network position.** A self-hosted agent typically sits inside the VPC with routes to databases, internal services and management endpoints that are not reachable from the internet. This is often more valuable than the credentials.
6. **The ability to persist** - modify the runner's tooling, install a hook, alter the base image the runner uses - so removal requires rebuilding, not cleaning.
7. **The OIDC token endpoint**, if `id-token: write` is available, letting them assume roles without any stored key at all.

**Which controls limit the damage:**

| Control | Effect |
| --- | --- |
| **Ephemeral runners** (Q34) | Removes persistence and cross-job secret leakage. The single highest-value control. |
| **OIDC instead of stored keys** (Q234) | There is no long-lived credential to steal; tokens are minutes long and scoped to one job. |
| **Per-service, per-environment roles with `sub` conditions** (Q236) | Compromising the agent that builds service A does not give access to service B or to production. |
| **GitOps pull-based deployment** (Q150) | The agent has **no cluster credentials at all** - the worst case is a git commit, which is reviewable and revertible. |
| **Environment protection rules with required reviewers** | Production credentials cannot be obtained without a human approval the agent cannot forge. |
| **SLSA L3 / isolated provenance generation** (Q59) | Provenance is generated by a component the build cannot influence, so a tampered artifact fails verification rather than being blessed by it. |
| **Signing keys in an HSM or keyless with short-lived certificates** | The key cannot be exfiltrated for later use. |
| **Network segmentation of the runner subnet** | Limits lateral movement, which is often the real objective. |
| **Egress filtering and monitoring on runners** | Detects exfiltration, which is otherwise invisible. |
| **Reproducible builds** (Q12) | Independent rebuilding detects a tampered artifact - the only control that catches a build-time backdoor after the fact. |
| **Audit logging of OIDC assumptions and registry pushes** | Detection and scoping during response. |

The framing worth stating: **your build system is a production system with production privileges.** Most organizations secure production carefully and run CI as if it were a developer tool, and that asymmetry is the whole attack.

### Q246. Compliance as code

The goal is that **evidence is a query, not a project**. Instead of an engineer screenshotting a settings page a week before the audit, every control emits a machine-readable artefact as a side effect of normal operation.

**How I would build it:**

1. **Map each control objective to a pipeline artefact.** "Changes are peer-reviewed" → the merge commit's approval record. "Only approved artifacts run in production" → the admission controller's verification decisions. "Access is least-privilege" → the IAM policy and its Terraform history. Write the mapping down; it is the thing you hand the auditor.
2. **Make the pipeline emit structured evidence**, not just logs: for every deployment, a record containing the commit SHA, the approvers, the check results, the image digest, the provenance attestation, the policy evaluation results, the deployment timestamp, and the deploying identity. One JSON document per release, stored immutably.
3. **Store it in append-only storage** with object lock, so it is tamper-evident. Signed provenance in a transparency log (Q58) is even better, because tamper-evidence is cryptographic rather than administrative.
4. **Policy as code produces the control test.** The OPA/Kyverno policies *are* the control statements, and their evaluation results *are* the test evidence - continuously, for every change, rather than a sample of 25 changes once a year. This is a stronger control than sampling, and the argument to make to the auditor.
5. **Continuous configuration assessment** - AWS Config rules, cloud posture management - for the infrastructure controls, with the compliance state as a time series rather than a point-in-time check.
6. **A queryable index.** The auditor's question is "show me evidence for these 25 changes", so you need to go from a change identifier to its full evidence bundle in one query. This is the part that turns a pile of artefacts into an audit-ready system.
7. **Generate the report.** A scheduled job that produces the control-evidence summary for the period, so audit preparation is running a job rather than a fortnight of chasing.

**The organizational move** that matters more than the tooling: bring the auditor in early and agree the evidence format *before* building it. An auditor who has agreed that a signed provenance attestation satisfies a control will accept it; one who is shown it for the first time in the audit will ask for the screenshot anyway.

### Q247. Separation of duties in an automated pipeline

The control objective is that **no single person can unilaterally put arbitrary code into production**. It is not that a machine must not deploy - it is that the *authorization* and the *execution* must be separable, and that one individual cannot supply both.

**How it is satisfied when a machine performs the deploy:**

1. **The authorization is the code review.** The author cannot approve their own pull request; branch protection enforces it; the approval is recorded against a verified identity. That is the separation, and it happens before the machine does anything.
2. **The machine has no discretion.** The pipeline deploys exactly what is on the protected branch, by a defined process, with no ability to deploy anything else. An automated actor that cannot make a choice cannot violate separation of duties - it is a mechanism, not a party.
3. **Nobody can bypass the machine.** This is the load-bearing part: **direct human access to deploy must be removed**, or the separation is voluntary. No `kubectl apply` from a laptop, no console changes, no push access to the deployment branch. With GitOps this is structural - the cluster only accepts what the reconciler applies, and the reconciler only reads the protected branch (Q162).
4. **The pipeline definition is itself protected.** If an engineer can change the workflow that deploys, they can deploy anything - so workflow files need CODEOWNERS and the same review requirement. This is the gap auditors find.
5. **Elevated actions require a second party**: GitHub Environments with required reviewers for production, so obtaining the deployment credential needs an approval from someone other than the author.
6. **Break-glass is separated too**: emergency access is time-bounded, requires a second approver or produces an immediate alert to a different team, and generates a review afterwards.
7. **Everything is attributable** (Q244), so the separation is demonstrable rather than asserted.

The argument to make to a control owner: this is **stronger** than the manual equivalent, because a human deployer can always deviate from the runbook and an automated one cannot, and because every instance is evidenced rather than a sample.

### Q248. Security controls from commit to pod, for regulated data `[A]`

**Commit**
1. Signed commits; enforced verified identity.
2. Pre-commit and server-side push protection for secrets; historical scanning of every repository (Q233).
3. Branch protection: no self-approval, CODEOWNERS on pipeline and infrastructure paths, dismiss stale approvals, no force push, no admin bypass (Q26).

**Build**
4. Ephemeral, isolated runners; no untrusted code in privileged contexts (Q33, Q235).
5. Pinned dependencies with lock files and checksums; internal artifact proxy with exclusive routing for internal namespaces (Q50-52).
6. Third-party actions pinned to SHAs and allow-listed (Q237).
7. SCA, SAST and secret scanning as gates on reachable-critical findings; the rest to a triage queue with an SLA (Q54-55).
8. SBOM generated at build; provenance attestation generated by an **isolated** builder (SLSA L3); image signed keylessly with identity claims (Q58-60).

**Artifact and promotion**
9. Immutable tags; everything referenced by digest (Q7).
10. Registry rescanning continuously against new CVEs, correlated to what is running (Q238).
11. Promotion is a reviewed pull request to the environment's manifest directory; approval by a second party; the PR is the change record (Q162).

**Deploy**
12. GitOps pull-based reconciliation; **no cluster credentials outside the cluster** (Q150).
13. Admission control: signature and provenance verified with pinned identity, digest references required, images only from our registry, Pod Security `restricted`, required ownership labels, default-deny NetworkPolicy generated (Q239).
14. Progressive rollout with automated analysis and abort (Q137).

**Runtime**
15. Workload identity for every credential; no static secrets in the cluster; secrets from an external store, mounted as files (Q123, Q128).
16. Default-deny network policy, mTLS between services, egress restricted and monitored (Q107).
17. eBPF runtime detection and, for the highest-risk namespaces, enforcement (Q243).
18. Encryption at rest with KMS for etcd and for data stores; encryption in transit everywhere.
19. Centralized, joinable audit logging with immutable retention (Q244).

**If asked to cut half**, the ones I would fight for, and why - they are the controls that either prevent the highest-likelihood attacks or that make everything else verifiable:

1. **Secret scanning with push protection.** It prevents the most common real breach by a wide margin, and it costs nothing.
2. **OIDC / workload identity everywhere, no static credentials.** Removes the entire class of stolen long-lived credentials, in CI and at runtime.
3. **Branch protection with mandatory second-party review, including on pipeline files.** The authorization control that everything else assumes.
4. **Ephemeral runners.** Without them, one compromised build compromises everything that touches that agent (Q245).
5. **GitOps pull-based deployment.** Removes production credentials from CI entirely, which is the largest single reduction in blast radius available.
6. **Pod Security `restricted` plus default-deny NetworkPolicy.** Cheap, platform-level, and they bound what a compromised workload can do.
7. **Centralized audit logging.** Not preventive, but without it you cannot detect, scope or prove anything - and during an incident it is the difference between "we contained it" and "we do not know".

**What I would give up first**, honestly: SLSA L3 isolated provenance (L2 retains most of the value for a fraction of the constraint), runtime enforcement as opposed to detection, DAST in the pipeline, and CVE-based admission blocking - which produces more operational disruption than security benefit until the estate is already clean.

*Hook: a security control you cut or deferred deliberately, and the reasoning you documented.*

---

## 16. Cost, FinOps and platform efficiency

### Q249. Where the spend goes

Typical ranking for a Kubernetes estate on a cloud provider:

1. **Compute (EC2 / node instances)** - usually **50-70 percent**. Driven by node count, which is driven by pod *requests*, not usage (Q251).
2. **Managed data services** - RDS, ElastiCache, OpenSearch, MSK. Often **15-30 percent** and frequently the largest single line item after compute. Provisioned for peak, running 24/7, and rarely right-sized.
3. **Storage** - EBS volumes (including orphaned ones), snapshots, S3. **5-15 percent**, and snapshots grow silently forever.
4. **Data transfer** - **5-15 percent**, and the least understood (Q256).
5. **Load balancers, NAT gateways, and other per-hour networking** - individually small, collectively significant. A NAT gateway at ~$0.045/hour plus per-GB processing, multiplied by AZs and environments, is a surprising number.
6. **Observability** - metrics, logs and traces, whether self-hosted (compute and storage) or SaaS (per-host, per-GB). **5-20 percent** and the fastest-growing line in most estates (Q200).
7. **The EKS control plane** itself - trivial per cluster, non-trivial multiplied by clusters and environments.

**What teams consistently forget:**

- **Non-production**, which is routinely 30-50 percent of total spend and is running at full size overnight and at weekends (Q257).
- **NAT gateway data processing charges**, which catch estates where every pod's outbound traffic - including image pulls and telemetry egress - crosses a NAT gateway.
- **Cross-AZ data transfer** between pods (Q256).
- **Orphaned resources**: unattached EBS volumes, old snapshots, idle load balancers left by deleted Services, unused elastic IPs, and images in the registry (Q10).
- **Observability**, because it is billed to a platform team and grows with the estate rather than with traffic.

### Q250. Cost attribution without chargeback theatre

**Attribution mechanism:**

1. **Node cost is known** - instance type, lifecycle (spot or on-demand), and hourly price. Divide it by the node's allocatable capacity to get a cost per CPU-hour and per GiB-hour.
2. **Allocate to pods by the maximum of requests and usage**, per resource, per hour. Requests are what reserved the capacity, so a pod requesting 2 CPU and using 0.1 should be charged for 2 - that is the whole incentive structure. Using the max of the two also captures a pod with no requests at all.
3. **Idle node capacity** - the difference between node cost and the sum of allocated pod cost - is a real number that has to go somewhere. Either amortize it across teams proportionally, or (better) hold it as a **platform line item** so it is visible as the efficiency gap rather than hidden in team bills.
4. **Shared services** - ingress, DNS, the observability stack, the GitOps controller - allocated proportionally or held centrally.
5. **Non-Kubernetes resources** attributed by **tags**, which is why mandatory ownership labels and tags (Q239) are the precondition for the whole exercise.
6. Tooling: OpenCost / Kubecost implements exactly this, and the cloud provider's cost allocation tags cover the rest.

**The unit I report** is the important part. Absolute spend per team is nearly useless - it goes up when the business grows, and it rewards teams that do less. Report:

- **Cost per unit of business value**: cost per 1,000 requests, per order, per active user, per tenant. This is the number that makes an increase interpretable, and it is the only one a product owner can act on.
- **Efficiency ratio**: usage divided by requests. A single percentage that says "how much of what you reserved did you use", directly actionable and directly comparable.
- **Trend, not level.** Month-on-month change in cost per unit, so growth is separated from waste.

**Why not chargeback theatre**: an internal invoice that nobody can pay and nobody can refuse creates finance overhead and resentment, not behaviour change. **Showback with a good unit metric changes behaviour**; formal chargeback only helps when teams have real budget authority and can trade cost against other priorities. I would start with showback, a visible dashboard and a per-team efficiency number, and only introduce chargeback if the organization already runs teams as cost centres.

### Q251. Requests versus usage

**Measuring the gap:**

```promql
# Cluster-wide CPU request efficiency
sum(rate(container_cpu_usage_seconds_total[7d]))
  / sum(kube_pod_container_resource_requests{resource="cpu"})

# Per-workload memory over-provisioning
sum by (namespace, workload) (container_memory_working_set_bytes)
  / sum by (namespace, workload) (kube_pod_container_resource_requests{resource="memory"})
```

The nuance: **use different statistics for the two resources.** For CPU, compare requests against a high percentile (p95-p99) of usage over a week or more, because CPU is compressible and bursts matter. For memory, compare against the **maximum** working set over the period, because memory is incompressible and sizing to an average gets you OOMKilled (Q94). Sizing memory on the mean is the most common right-sizing mistake.

VPA in recommender mode (Q115) does this computation and is the easiest source of per-workload numbers.

**Realistic target utilization for a production node pool**: **60-75 percent of allocatable CPU requested**, with actual usage 40-60 percent of allocatable. Higher than that and you have no room for a rollout surge, an AZ failure, or an autoscaling delay (Q218). Much lower and you are paying for air.

The distinction that matters: there are **two separate gaps**, and they have different fixes.

- **Requests versus usage** (pods asking for more than they use) - fixed by right-sizing, and it is the bigger number in most estates. Typical starting point is 20-35 percent efficiency, i.e. requests are three to five times usage.
- **Requests versus node capacity** (bin-packing waste, stranded capacity) - fixed by better instance shapes, consolidation, or Karpenter (Q112).

You can have perfect bin-packing of wildly over-sized requests, and the nodes will look 95 percent "allocated" while running at 15 percent CPU. Reporting only allocation makes the estate look efficient when it is not.

### Q252. Reduced requests, latency got worse `[T]`

Two mechanisms, and they are different:

**1. The CPU request determines the CFS share.** Under contention, the kernel allocates CPU proportionally to `cpu.shares`, which Kubernetes derives directly from the *request*. Halving the request halves the pod's guaranteed share when the node is busy. On an idle node nothing changes - which is why this is invisible in testing and appears at peak, when it matters most. The pod is not throttled by a limit; it is simply losing the competition for CPU against its neighbours.

**2. The request changed what the JVM thinks the machine is.** If the change also introduced or reduced a **CPU limit**, the JVM's `availableProcessors` drops (Q76), which resizes the GC thread pool, the JIT compiler threads, the ForkJoinPool common pool, and any application thread pool sized from it. Fewer GC threads means longer stop-the-world pauses; a smaller common pool means queueing in parallel streams and `CompletableFuture` chains. And if a limit is now in play, CFS throttling appears in bursts (Q92).

There is a third, related mechanism worth mentioning: **memory** request reduction changes the pod's **QoS class** from Guaranteed to Burstable, which makes it a preferred eviction candidate under node pressure (Q91) - so the pod is now periodically evicted and restarted, and cold-start latency shows up in the tail.

**The lesson for right-sizing**: requests are not only an accounting number, they are a **scheduling and runtime input**. Right-sizing must be validated against latency percentiles under production load, not just against a usage graph, and it should be done incrementally with observation between steps. The diagnostic to reach for is `container_cpu_cfs_throttled_seconds_total` plus GC pause time, and the comparison is p99 before and after - not average CPU.

### Q253. Spot and Graviton

**Spot** - interruptible capacity at 60-90 percent off, reclaimed with a **two-minute warning**.

*Required in the application*: it must tolerate being killed at any time. Concretely - stateless or with state held externally; correct graceful shutdown within the notice period (Q89-90); idempotent work so an interrupted request or message can be retried; no long-running in-memory work that cannot be checkpointed; and connection draining that actually functions.

*Required in the cluster*:
- **Diversification across instance types and AZs** - the single most effective control, because spot pools are reclaimed independently. Karpenter does this natively; with node groups it means many instance types per group.
- **A node termination handler** consuming the interruption notice and cordoning and draining the node immediately, so the two minutes are used rather than wasted.
- **PodDisruptionBudgets** so a reclaim cannot take out a whole service.
- **Topology spread across zones and node types**, so a pool reclaim does not take all replicas.
- **A mixed strategy** - an on-demand or reserved baseline sized to the minimum acceptable capacity, with spot for everything above it. Never 100 percent spot for a production service.
- **Fallback to on-demand** when spot is unavailable, which Karpenter handles and which a static node group does not.

**Graviton** (ARM64) - typically 20-40 percent better price-performance.

*Required*: **multi-architecture images**. That means `docker buildx` producing an image index covering `linux/amd64` and `linux/arm64`, and CI that builds both (either on ARM runners, which is fastest, or via emulation, which is slow). Then every dependency must have an ARM64 build - the JVM does, and most of the ecosystem does now, but **native libraries are the risk**: an old JNI dependency, a native codec, or a vendored binary with no ARM build will fail. The failure is usually at start-up and obvious, which is the good case; the bad case is a performance regression in a native library's ARM path.

*Required in the cluster*: node selectors or Karpenter requirements on `kubernetes.io/arch`, and either a migration where everything is multi-arch or careful scheduling so an amd64-only image never lands on an ARM node.

The pragmatic sequencing: **Graviton first** (it is a permanent, low-risk saving once images are multi-arch), **spot second** (bigger saving, real operational requirements), and prove both on non-production and on interruption-tolerant workloads before touching a tier-1 service.

### Q254. Commitments with an uncertain roadmap

**The instruments:**

- **On-demand** - full price, no commitment.
- **Savings Plans** - commit to a dollar-per-hour of spend for 1 or 3 years. **Compute Savings Plans** are the flexible kind: they apply across instance families, sizes, regions, OS, and across EC2, Fargate and Lambda. **EC2 Instance Savings Plans** are cheaper but lock you to a family and region.
- **Reserved Instances** - commit to specific instance attributes; largely superseded by Savings Plans for compute, still relevant for RDS, ElastiCache and OpenSearch, where Savings Plans do not apply.
- **Spot** - not a commitment; a different risk trade (Q253).

**How I decide the level:**

1. **Find the floor.** Plot hourly spend over the last 6-12 months and find the level below which usage never falls - the **always-on baseline**. That is what you can commit to with near-zero risk, and it is usually 50-70 percent of total.
2. **Commit to the baseline, not the average.** The asymmetry matters: an under-commitment costs you the discount you did not take (a few percent); an **over-commitment is paid whether or not you use it**, which is a pure loss. Given uncertainty, commit conservatively.
3. **Prefer 1-year over 3-year** when the roadmap is uncertain. The extra discount for 3 years is real but modest (roughly 10-15 percentage points more), and three years is longer than most architectural decisions survive. A migration to Graviton, to Fargate, or to a different region can strand a 3-year commitment.
4. **Prefer Compute Savings Plans over Instance Savings Plans or RIs.** The flexibility premium is small and it is precisely what protects you against roadmap change - a Compute Savings Plan survives a move to ARM, to Fargate, or to a different instance family.
5. **Ladder the commitments.** Rather than one large 3-year purchase, buy in tranches that expire at staggered intervals. The portfolio then reprices continuously, you are never fully locked, and you can adjust as the trend becomes clearer.
6. **Account for the direction of the roadmap explicitly.** A planned right-sizing programme, a Graviton migration, or a workload moving to a managed service will all *reduce* the baseline. Commit to the post-optimization floor, not the current one - otherwise your efficiency work makes the commitment worse.
7. **Monitor coverage and utilization** as ongoing metrics: coverage (what fraction of eligible spend is covered) and utilization (what fraction of the commitment is used). Utilization below 100 percent is money burned.

The framing: **commitments are a financial hedge on a technical forecast.** Buy conservatively, buy flexibly, ladder the maturities, and do the efficiency work first so you are not committing to your own waste.

### Q255. Right-sizing a JVM service

**Data needed:**

- **Memory working set over at least two weeks**, at the **maximum**, covering a full business cycle including month-end and any batch peak.
- **CPU usage at p95 and p99**, plus the **average**, over the same period.
- **CFS throttling** (`container_cpu_cfs_throttled_seconds_total`) - if it is non-zero, the current sizing is already hurting and the usage data understates demand.
- **JVM internals**: heap after full GC (the real live-set size), metaspace, thread count, direct memory, and GC pause time and frequency. Native Memory Tracking if the footprint is unexplained (Q75).
- **Latency percentiles**, as the outcome variable - the thing you must not regress.
- **Request rate**, so you can normalize and reason about cost per request.
- **Restart and OOMKill history**, which tells you whether the current limit is already marginal.

**The trap of sizing on average utilization:** a JVM's resource profile is bimodal and bursty.

- **CPU**: the average includes long idle periods; the bursts are GC, JIT and concurrent request handling. Sizing the request to the average guarantees contention exactly when work arrives (Q252), and sizing a *limit* to the average guarantees throttling (Q92). Size CPU requests to roughly **p95 of usage**, not the mean.
- **Memory**: sizing to the average is much worse, because memory is incompressible. Average working set says nothing about the peak, and the peak is what triggers the OOM kill. Size memory to **max working set plus a margin**, and set request equal to limit so the QoS class is Guaranteed and `MaxRAMPercentage` computes against a stable number (Q74, Q91).
- **The JVM will use whatever heap you give it**, so its memory usage is partly a *consequence* of the limit rather than a measurement of need. The real signal is the **live set after a full GC**, not the resident memory. A service showing 1.4 GB used with a 2 GB limit may have a 400 MB live set and simply not have needed to collect.

**The method**: derive candidate values from p95 CPU and max memory, apply them to a canary or a subset of replicas, watch latency percentiles and throttling for a full business cycle, then roll out. Iterate downward in steps rather than jumping to the computed minimum, and never right-size several services simultaneously - if latency regresses you want to know which change did it.

### Q256. Data transfer and observability costs

**Why both grow super-linearly with service count:**

**Data transfer.** Decomposing a monolith turns in-process method calls into network calls. If a user request that previously touched one process now fans out across *n* services, and those services are spread across *k* availability zones, then in the naive case roughly **(k-1)/k of every inter-service hop crosses an AZ boundary** and is billed in both directions. The number of hops grows with the interaction density of the service graph, which grows faster than the service count - so traffic grows roughly with the *edges* of the graph rather than its nodes. Add a service mesh (every hop now traverses two proxies), retries, and chatty APIs that require several calls where one would do, and the multiplier compounds.

**Observability.** Each new service adds its own metric series (multiplied by every label dimension), its own log stream, and - crucially - **a new span in every trace that passes through it**. So trace volume grows with the number of services *on the path*, not with the number of services. Metrics grow with services × instances × metrics × label cardinality, which is a product of four growing terms. And a mesh doubles the span count and adds a full set of proxy metrics per workload.

**What I do about data transfer:**

1. **Topology-aware routing** - `trafficDistribution: PreferClose` on Services (or the older topology hints), which keeps traffic within the zone when a healthy endpoint exists there. This is the single biggest lever and it is one field.
2. **VPC endpoints** for S3, ECR, and other AWS services, so that traffic does not traverse the **NAT gateway** - which charges per GB processed on top of the transfer. Image pulls through a NAT gateway are a classic large, invisible line item.
3. **Reduce chattiness** - batch APIs, avoid N+1 across service boundaries, and cache aggressively at the caller.
4. **Compression** on inter-service payloads, and a more compact serialization where volume justifies it.
5. **Co-locate** tightly-coupled services and their data.

**What I do about observability cost**: everything in Q200 - filter and sample at the Collector before egress, drop high-cardinality labels, tail-sample traces, and attribute the spend per team so it has an owner.

The structural point worth making: both of these are **consequences of architecture**, so the largest lever is not a configuration setting - it is having fewer, coarser service boundaries in the request path (Q217 makes the same argument from an availability angle).

### Q257. Non-production spend

**Shut down entirely:**
- **Development and test clusters outside working hours.** Scale node groups to zero at 19:00 and back at 07:00 on weekdays, and off entirely at weekends. That is roughly **70 percent of the hours in a week**, so it is a 70 percent saving on those environments for one scheduled job. This is the largest and easiest win in the whole category.
- **Ephemeral per-PR environments**, with a hard TTL and automatic deletion on branch merge or close. Untracked PR environments are a common source of long-tail spend.
- **Idle databases and caches** in dev - stop RDS instances (they auto-restart after 7 days, so it needs a scheduler), delete unused ElastiCache clusters.
- **Anything with no owner tag**, after a notice period. A quarterly sweep with a two-week warning finds a surprising amount.

**Shrink:**
- **Instance sizes and replica counts** - dev does not need three replicas or production instance types. Single-AZ, single-replica, smallest viable instances.
- **Use spot for everything** in non-production; interruption there costs nothing.
- **Shorter retention** for logs, metrics, backups and snapshots.
- **Smaller data volumes** - a subset of production data rather than a full copy, which also reduces the compliance surface.
- **Shared clusters with namespace isolation** rather than a cluster per team (Q117), since the control plane and platform components are a fixed cost per cluster.

**Must stay production-shaped**, and this is the important half - because the point of staging is to prove things, and a staging environment that differs in the wrong ways proves nothing:

- **Same Kubernetes version and add-on versions**, so an upgrade is genuinely rehearsed.
- **Same policy set** - admission control, network policies, Pod Security level, RBAC model. A manifest that passes in staging must pass in production.
- **Same architecture**: multi-AZ topology if production is multi-AZ, same ingress path, same mesh configuration, same TLS. Scale can differ; **shape must not**.
- **Same deployment mechanism** - identical pipeline, identical GitOps flow, identical progressive rollout. Otherwise the release process is untested.
- **Same instrumentation** - staging is where you validate that dashboards and alerts work.
- **Realistic data volumes for at least one environment**, because query plans and index behaviour are data-dependent (Q220).

The rule I would state: **you may shrink capacity in non-production, but you may not simplify architecture.** Every architectural difference between staging and production is a defect that will be found in production.

### Q258. Cost down 30 percent, incidents doubled `[T]`

The likely trades, in order of probability:

1. **Headroom.** The most likely single cause. Right-sizing to observed usage removes the buffer that absorbed traffic spikes, autoscaling delay (Q114), and AZ failure (Q218). The service now runs close to saturation, so latency is non-linear in load and every ordinary variation becomes an incident.
2. **Redundancy.** Replica counts reduced, multi-AZ collapsed to single-AZ, a standby removed, a read replica deleted. Nothing fails until something fails, and then there is no capacity to fail into. This is the trade with the worst tail: it is invisible until it is an outage.
3. **CPU requests reduced too far**, producing contention and throttling (Q252) - latency regressions that look like application problems.
4. **Memory requests reduced**, producing OOMKills and evictions under load, and moving pods to Burstable QoS so they are evicted first under node pressure (Q91).
5. **Spot adopted without the prerequisites** (Q253) - insufficient diversification, no on-demand baseline, missing PDBs, or graceful shutdown that does not work. Reclaims now cause user-visible errors.
6. **Observability cut.** Retention shortened, sampling increased, metrics dropped. Incidents may not actually have doubled - **detected** incidents may have changed, or, more likely, incidents now take much longer to diagnose so more of them become significant. Cutting observability does not create incidents; it removes your ability to prevent and shorten them.
7. **Non-production degraded past the line in Q257** - staging no longer production-shaped, so defects reach production that staging would have caught.
8. **Aggressive consolidation** (Karpenter or cluster autoscaler) causing constant node churn, so pods are disrupted far more often and every weakness in graceful shutdown is exercised repeatedly.

**The diagnosis approach**: correlate the incident timeline against the change timeline - which optimization landed, and did incident rate change after it? Then classify incidents by mechanism (saturation, eviction, OOM, node reclaim, diagnosis time) and map each to the corresponding change.

**The lesson to state**: cost optimizations must be **measured against reliability outcomes, not just the bill**, and they should be rolled out incrementally with an observation period, exactly like a code change. A 30 percent saving that doubles incident load is almost certainly a net loss once engineering time and customer impact are priced - which is the calculation nobody does up front.

### Q259. Efficiency as an SLO

**Setting the target:**

1. **Choose the unit**: cost per 1,000 requests, per order, per active user, or per tenant - whatever maps to how the business measures value. It must be a *ratio*, so that growth does not look like regression.
2. **Establish the current baseline** and its natural variance over a couple of months, so the target is grounded rather than aspirational.
3. **Set the target as a ceiling on the trend**, not a fixed number: "cost per 1,000 requests does not increase quarter on quarter" or "declines by 5 percent per quarter". A fixed absolute number goes stale immediately and punishes legitimate feature work.
4. **Define it per service**, owned by the team that controls the spend, and roll up to a platform-level number.
5. **Pair it with a reliability constraint**, explicitly: the efficiency target is only valid while the availability and latency SLOs are met. This is what stops Q258.

**Making it visible without making it a stick:**

- **Showback, not chargeback** (Q250). Publish the number on the same dashboard as the reliability SLOs, so it sits alongside the other measures of a well-run service rather than in a finance report.
- **Report efficiency ratio (usage/requests) alongside cost.** It is actionable in a way that a currency figure is not - a team can see "we are using 22 percent of what we reserved" and know exactly what to do.
- **Give teams the tools and the recommendations**, not just the number: VPA recommendations, a right-sizing runbook, an idle-resource report. A metric with no lever attached generates resentment.
- **Celebrate improvements publicly** and treat regressions as a conversation, not a penalty. The moment efficiency becomes something teams are punished for, they optimize the metric rather than the cost - by moving spend to a shared line item, or by cutting the things that are invisible, like observability and headroom.
- **Set it as a guardrail, not a goal.** The target is "do not regress", not "minimize". A team that hits an aggressive efficiency target by removing redundancy has satisfied the metric and damaged the business.
- **Fund the work.** If efficiency is a stated objective, it needs sprint capacity like anything else; otherwise it is a wish.

The framing: **an efficiency SLO is a constraint on how the service is run, in the same family as the availability SLO - and like the error budget, it is meant to be spent deliberately** (on headroom, on redundancy, on observability) rather than minimized.

### Q260. 25 percent reduction in two quarters `[A]`

**First, get the facts and set expectations.** Break down the bill by service, environment, team and resource type, and separate **growth** from **waste**. If the business is growing 30 percent, a flat bill is already a 25 percent per-unit reduction, and agreeing the metric - absolute or per-unit - before starting is the most important conversation in the whole exercise.

**Quarter 1 - the changes with no architectural risk. Target: 15-18 percent.**

| Action | Expected | Risk |
| --- | --- | --- |
| **Shut down non-production out of hours and at weekends** (Q257) | 5-8% of total | None |
| **Delete orphaned resources** - unattached volumes, old snapshots, idle load balancers, unused environments, registry garbage | 2-4% | None |
| **Right-size the worst offenders** using VPA recommendations, top 20 workloads, incrementally with latency observation (Q255) | 4-6% | Low, if done incrementally |
| **Buy Savings Plans on the measured baseline** (Q254), conservatively and laddered | 5-10% on covered spend | Financial only |
| **Observability cost reduction** - drop high-cardinality metrics, filter health-check telemetry at the Collector, tier retention (Q200) | 1-3% | Low, if signal is preserved |
| **VPC endpoints and topology-aware routing** to cut NAT and cross-AZ transfer (Q256) | 1-2% | None |

**Quarter 2 - structural changes. Target: another 8-12 percent.**

- **Graviton migration** for services with multi-arch-clean dependencies: 15-25 percent on that compute.
- **Spot for interruption-tolerant workloads** - batch, CI runners, non-production, and stateless services once PDBs and graceful shutdown are verified (Q253).
- **Karpenter for consolidation and better bin-packing** (Q112).
- **Right-size the managed data services**, which are usually the second-largest line and the least examined.
- **Establish per-team showback with a cost-per-unit metric** (Q250, Q259), so the reduction does not silently reverse in quarter 3. This is the durable part.

**What I would refuse to cut:**

1. **Headroom and redundancy.** Multi-AZ, N+1 capacity, replica counts on tier-1 services. This is where a cost programme becomes an availability incident (Q258), and I would rather miss the target and say why.
2. **Observability below the level needed to detect and diagnose.** I would cut *volume* aggressively - sampling, retention, cardinality - and refuse to cut *coverage* of SLO measurement, error capture and change events.
3. **Backups, backup testing, and cross-region backup isolation** (Q225-226).
4. **Security controls** - scanning, audit logging, secrets infrastructure.
5. **Staging's architectural fidelity** (Q257). Shrink it; do not simplify it.
6. **The reliability engineering capacity itself**, which is the thing that lets you run leaner safely.

**How I would present it**: with the achievable number, the confidence interval, and an explicit statement of what the last 5 percent would cost in risk if pushed for. If 25 percent is only reachable by cutting into the refusal list, I would say so, quantify the exposure, and offer the alternative - reaching 20 percent safely and the remainder over the following two quarters through architectural work. Committing to a number I can only hit by taking undisclosed risk is how a cost programme becomes an outage with a paper trail.

*Hook: a cost reduction you delivered, the number, and the thing you refused to cut.*

---

## 17. Platform engineering, design exercises and leadership

> Q261-265 are worked as full design exercises in [scenario-questions.md](scenario-questions.md), Part B. Read the question, spend twenty minutes designing out loud, then compare. Q266-270 are story questions with no scripted answer - use STAR-L and your own material.

### Q266-270. Story questions

No model answer is scripted for these, on purpose - they must be your own. Use **STAR-L** (Situation, Task, Action, Result, **Learning**), keep each to two or three minutes, and always quantify the Result.

The stories to prepare are listed in [README.md](README.md) under "Your delivery story bank". Worked examples of the *style* are in [scenario-questions.md](scenario-questions.md), Part C.

