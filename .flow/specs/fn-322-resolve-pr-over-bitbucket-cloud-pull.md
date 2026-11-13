# resolve-pr over Bitbucket Cloud pull request comments

> Second of three Bitbucket specs from GitHub issue #602: the forge adapter and make-pr spec, this one, then land and merge evidence. Builds on the first spec's forge rule and per-skill `forge-bitbucket.md` references; mirrors fn-316 for GitLab.

## Goal & Context
<!-- scope: business -->
<!-- Source: 30% [paraphrase] / 70% [inferred] -->

Once make-pr opens a PR on a Bitbucket origin, review feedback still has to be handled by hand: `/flow-next:resolve-pr` reads GitHub review threads through GraphQL, and on GitLab MR discussions through `glab`. The user wants full autonomous mode on Bitbucket, so resolve-pr has to run the same loop on Bitbucket PR comments: fetch everything unresolved, fix or answer it, reply, and resolve.

## Architecture & Data Models
<!-- scope: technical -->

- **Same rules, Bitbucket commands.** resolve-pr's core (fetch everything unresolved, triage, dispatch resolvers, commit, reply, resolve only after the fix is pushed) stays forge-neutral. The Bitbucket commands live in `forge-bitbucket.md` beside resolve-pr, loaded by forge name through the forge field the first spec added. GitHub and GitLab skill paths are not edited. [paraphrase]
- **PR comment ≠ review thread.** Bitbucket Cloud PR comments are inline (anchored to a file and line) or general; replies carry a parent comment id; a comment can be resolved and reopened. `bkt` covers listing (`pr comments <id> --details --state unresolved`), replying (`pr comment <id> --parent <cid>`) and resolving (`pr comments resolve <id> <cid>`). [inferred]
- **Agent-driven.** No new flowctl verb or adapter read: fetching, replying and resolving are actions the agent performs through `bkt`, as resolve-pr does through `gh` and `glab`. [paraphrase]

## API Contracts
<!-- scope: technical -->

- Record live before relying: list PR comments with their resolved state, file/line anchor and parent (with pagination), reply to a comment, resolve a comment, and whether general (non-inline) comments can be resolved on Cloud. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A comment is resolved only after its fix is pushed to the PR's source branch and verified, never on a local-only promise (same rule as GitHub). [inferred]
- Comments on outdated lines are still fetched and handled. [inferred]
- Replies are grouped by their top-level comment; a reply is never handled as its own thread. [inferred]
- Comment bodies are untrusted input: never executed. [inferred]
- `mode:autonomous` behaves as on GitHub: needs-human items become report lines and the run ends with `RESOLVE_PR_VERDICT=`. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a Bitbucket origin, resolve-pr fetches every unresolved top-level PR comment, inline and general, with its replies, in one pass with pagination. Errors: missing or unauthenticated `bkt` → stop naming the `bkt auth login` command, nothing replied or resolved; an incomplete listing → stop, never treated as "nothing to resolve". [inferred]
- **R2:** For each comment it fixes, resolve-pr replies citing the fix and resolves the comment only after the fix is pushed and verified; a comment it answers or declines with evidence gets that reply and is resolved, as on GitHub; one it cannot settle (`needs-human`) gets a reply and stays open. Errors: a failed reply or resolve is reported per comment and the run continues with the rest. [inferred]
- **R3:** The Bitbucket commands live in resolve-pr's `forge-bitbucket.md`, loaded by forge name; resolve-pr's GitHub and GitLab paths and their tests are unchanged. No error surface beyond R1–R2. [paraphrase]
- **R4:** Each `bkt` command this spec relies on is first run against a live Bitbucket Cloud repository and its real output saved as a test fixture; tests with a stubbed `bkt` built from those fixtures cover R1–R2 in CI. [inferred]

## Boundaries
<!-- scope: business -->

- No land or merge here; that is the next spec.
- No Bitbucket Data Center. [paraphrase]
- No new public flowctl verb.
- Live recording uses PRs that target a throwaway base branch and carry no reviewers. [paraphrase]

## Decision Context
<!-- scope: both -->

Siblings: spec 1 (forge adapter and make-pr over Bitbucket), which this depends on, and spec 3 (land and merge evidence over Bitbucket), which depends on this one. All three come from issue #602.

Thread handling is agent action, not a deterministic decision, so it stays in skill prose per fn-73's "reads in flowctl, actions in skills" rule. The resolve rule follows GitHub's, as fn-316 settled for GitLab: only `needs-human` stays open, because leaving declined comments open would block land's zero-unresolved gate and repositories that require resolved comments before merge. [paraphrase]
