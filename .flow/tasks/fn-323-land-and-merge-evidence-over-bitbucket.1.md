---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-323-land-and-merge-evidence-over-bitbucket.1 Implement land and merge evidence over Bitbucket Cloud pull requests

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The Bitbucket adapter gains readiness (bkt merge checks, worst build status on the head via links.commit.href, approvals, draft), merge evidence (merged rows with the merge transition's time and the full merge commit; changed paths from diffstat) and spec approval (participants, account ids). land's forge-bitbucket.md gates, re-reads the head before a squash merge and confirms the merged source commit is the gated head. After the whole-branch review every Bitbucket listing pages through one helper (next links, size check) and one shared origin parser serves preflight, resolve-pr and land.

Live: sandbox PR 32 gated ready and merged by squash, merged source == gated head, merge evidence classified merged; a conflicting PR reads ready false.

stage: impl-review - ran (codex, gpt-6.1-sol): NEEDS_WORK (5) -> fixed -> re-review NEEDS_WORK (1, fixed) -> whole-branch review (focus AI slop / maintainability) NEEDS_WORK (6: 4 fixed structurally, 1 spec amended, 1 partly recorded) -> re-review: only R6 recording gap left; logged-out answer recorded, populated builds and approvals deferred in the specs (sandbox has no pipelines, no second reviewer)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 0f7d9d678a6e31db7b39533ed643cb7745442324, efdcc660d8c5ac54759ea67a3aeeb4dfaa90eee5, 1aa7866c4436cb0b84468dd2caeeee54b0d3eb9c, 959e47834d92443323308ba0614ffa1ab880f556, 05ca577deefc644b44331512b282d584cf9a9866
- Tests: python3 -m pytest -q (15 files: forge, land/make-pr/resolve-pr bitbucket+gitlab, codex, flow auto/routing, prose, fences, make-pr close/auth) - 180 passed
- PRs: