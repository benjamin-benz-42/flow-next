---
satisfies: [R1, R2, R3, R4]
---
# fn-322-resolve-pr-over-bitbucket-cloud-pull.1 Implement resolve-pr over Bitbucket Cloud pull request comments

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
resolve-pr reads Bitbucket Cloud feedback through `get-bitbucket-comments` (every unresolved top-level comment, inline or general, with replies at any depth; Bitbucket's own outdated flag from the single-comment read; deleted and pending comments left out; short, malformed or unreadable pages fail closed), replies in thread and resolves through `reply-to-bitbucket-comment` / `resolve-bitbucket-comment`, named in `forge-bitbucket.md` (per-thread error handling, fork pushes to the source repository).

Live on sandbox PR 30: fetch reported the reopened inline thread with isOutdated true and its replies, then the scripts replied and resolved it; resolving twice succeeds. Measured: general comments are resolvable on Cloud; the listing omits inline.outdated.

stage: impl-review - ran (codex, gpt-6.1-sol): NEEDS_WORK (4 findings, all fixed) -> re-review SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 7efdb740ac986583794465ad2b3576ac7012a438, a2d068105e39dc63b8588a597ee0234bc3b07b69
- Tests: python3 -m pytest -q tests/test_resolve_pr_bitbucket.py tests/test_resolve_pr_gitlab.py tests/test_skill_prose_diet.py tests/test_unattended_skill_fences.py tests/test_codex_config_merge.py
- PRs: