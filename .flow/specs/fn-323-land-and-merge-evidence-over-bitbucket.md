# land and merge evidence over Bitbucket Cloud pull requests

> Third of three Bitbucket specs from GitHub issue #602: the forge adapter and make-pr spec, the resolve-pr spec, then this one. Mirrors fn-317 for GitLab.

## Goal & Context
<!-- scope: business -->
<!-- Source: 35% [paraphrase] / 65% [inferred] -->

With make-pr and resolve-pr working on Bitbucket, the last manual step of the loop is merging: `/flow-next:land` reads checks and readiness and merges through `gh` (GitHub) or `glab` (GitLab). On a Bitbucket origin there is no merge-readiness read, no merge evidence, and no approval read, so land cannot ship, a Jira-tracked spec never gets the merge evidence that drives terminal `Done`, and `spec.approval pr` reports "unsupported on this forge". The user wants full autonomous mode on Bitbucket; this spec closes the loop.

## Architecture & Data Models
<!-- scope: technical -->

- **Three more adapter reads.** The `bitbucket` adapter gains `readiness` (whether an open PR can merge now), `merge_rows` (merged PRs for a branch with merge time and merge commit, for tracker merge evidence) and `approval_rows` (approvers and merge identity, for `spec.approval pr`), all through `bkt` and mapped to the shapes the GitLab and GitHub adapters already return. Callers are unchanged. [paraphrase]
- **Actions in land's reference.** Checking builds and merging are agent actions in land's `forge-bitbucket.md` (`bkt pr checks`, `bkt pr mergeability`, `bkt pr merge`), loaded by forge name. GitHub and GitLab paths are not edited. [paraphrase]
- **Merge time is real.** Bitbucket's PR object carries no merge timestamp; `merge_rows` takes it from the PR's activity (the state change to merged) or the merge commit, never from `updated_on`. [paraphrase]
- **Approvals from participants.** A participant with `approved: true` is an approver; a participant whose state is `changes_requested` counts as requested changes, not approval. Merge identity is a stable account identifier, not a display name. [paraphrase]

## API Contracts
<!-- scope: technical -->

- Internal only; the read shapes are the ones the existing adapters return.
- Record live before relying: PR mergeability (clean, blocked, conflicting), build statuses for the head commit, PR merge with an explicit strategy and message, PR activity for a merged PR, the merge commit of a merged PR, and participants with approved and changes-requested states. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- `bkt pr mergeability` reports `UNKNOWN` and exits nonzero on API errors; that is "cannot tell", never "ready". [inferred]
- Repository merge checks (required approvals, passing builds, no unresolved tasks) are respected through mergeability; land never forces a merge past them. [inferred]
- The merge strategy follows land's existing rule; when the repository allows only some strategies, a refused strategy is a reported failure, not a silent fallback. [inferred]
- Short commit hashes from Bitbucket are resolved locally when possible; an unresolvable hash never matches a different commit. [inferred]
- A PR declined or superseded after approval is not merge evidence. [inferred]
- Live recording merges only into a throwaway base branch, never a real default branch, and adds no reviewers. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a Bitbucket origin, land reads whether the open PR can merge now (builds, repository merge checks, conflicts, unresolved comments) through `bkt` and merges it when every gate passes, following land's `forge-bitbucket.md`. Errors: missing or unauthenticated `bkt` → stop before any merge, naming the `bkt auth login` command; mergeability `UNKNOWN` or a failed read → not ready, reported; a refused merge → reported with Bitbucket's reason, nothing claimed as merged. [inferred]
- **R2:** For a merged Bitbucket PR, the merge evidence the tracker reads carries the real merge time and merge commit, so a Jira-tracked spec on a Bitbucket repo reaches terminal `Done` on merge as on GitHub. Errors: a merge time that cannot be determined is reported as unknown, never substituted with `updated_on`. [paraphrase]
- **R3:** Under `spec.approval pr` on a Bitbucket origin, approval is read from the merged spec PR's participants: approvers count, `changes_requested` does not, and the merger is a stable account identifier. Errors: a failed read → "not approved" with the reason, never a guess. [paraphrase]
- **R4:** `flow --auto` with land on a Bitbucket origin goes from an open PR to a merged one when the gates pass. [strategy:Autonomous mode] Errors: a gate that does not pass stops land with that gate named, as on GitHub. [paraphrase]
- **R5:** GitHub and GitLab behaviour and their tests are unchanged. No error surface beyond R1–R4. [paraphrase]
- **R6:** Each `bkt` command this spec relies on is first run against a live Bitbucket Cloud repository and its real output saved as a test fixture; tests with a stubbed `bkt` built from those fixtures cover R1–R3 in CI. [inferred]

## Boundaries
<!-- scope: business -->

- No Bitbucket Data Center. [paraphrase]
- No Bitbucket Pipelines management beyond reading build statuses for the gate. [inferred]
- No new public flowctl verb, no config key.

## Decision Context
<!-- scope: both -->

Siblings: spec 1 (forge adapter and make-pr over Bitbucket) and spec 2 (resolve-pr over Bitbucket PR comments), which this depends on. All three come from issue #602.

The stand-in a user wrote reported `updated_on` as the merge time, a display name as the merger, and only approvals as reviews; each of those would make merge evidence or spec approval wrong in a way a run cannot notice, which is why R2 and R3 name them. [paraphrase]

**Amended 2026-11-13 during work.** Live runs settled three points the spec left open. Bitbucket's merge call takes no expected head, so land re-reads the head right before merging and confirms afterwards that the merged source commit is the head it gated, stopping `NEEDS_HUMAN` otherwise. A repository with no builds reports none, which is nothing to wait for; builds a repository requires block in Bitbucket's merge checks instead. A failed build stops `BLOCKED` naming it: land does not repair or rerun Bitbucket builds, since their logs could not be recorded live on the sandbox (it has no pipelines). [inferred]

**R6 recordings deferred (2026-11-13).** Populated build statuses and approved or changes-requested participants are not recorded live: the sandbox repository has no pipelines and the test account cannot review its own pull requests. Their tests replay recorded responses with only those fields changed, to Bitbucket's documented shapes (a status names its commit through `links.commit.href`). Record them on a repository with pipelines and a second reviewer before relying on them further. [inferred]
