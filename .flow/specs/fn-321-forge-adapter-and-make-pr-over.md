# Forge adapter and make-pr over Bitbucket Cloud pull requests

> First of three Bitbucket specs from GitHub issue #602: this one (forge adapter, make-pr, and `flow --auto` up to an open PR), then resolve-pr over Bitbucket PR comments, then land and merge evidence. Same shape as the GitLab sequence fn-73 → fn-316 → fn-317.

## Goal & Context
<!-- scope: business -->
<!-- Source: 40% [paraphrase] / 60% [inferred] -->

A repo whose origin is on Bitbucket Cloud cannot run `flow --auto` at all. The pilot snapshot and the route judge list PRs for the spec branch through the forge adapters; no adapter claims `bitbucket.org`, so the read falls through to the GitHub adapter, `gh pr list` fails, `pr_exists` stays unknown, and the run stops on `NEEDS_HUMAN` with `pr_probe_failed` before the first stage. A user worked around it with a throwaway `gh` stand-in that answered only `gh pr list` from the Bitbucket REST API; with it, a run went through work and impl-review and routed to `all_done_make_pr`, then could go no further because make-pr calls `gh pr create`.

The user wants full autonomous mode on Bitbucket, contributed to the public repo. This spec makes Bitbucket a third forge next to GitHub and GitLab, so `flow --auto` on a Bitbucket Cloud origin ends at an open PR without any stand-in.

## Architecture & Data Models
<!-- scope: technical -->

- **fn-73's forge seam, one more adapter.** A `bitbucket` adapter joins the internal adapter registry with `list_prs`; Bitbucket Cloud's fixed hosts (`bitbucket.org`, `ssh.bitbucket.org`, `altssh.bitbucket.org`) claim the origin directly, so no `owns_host` probe is needed. flowctl callers dispatch through the registry and never name Bitbucket. No new public flowctl verb and no config key: the forge stays derived from the origin remote. [paraphrase]
- **`bkt` is Bitbucket's CLI.** Bitbucket has no first-party CLI comparable to `gh`/`glab`; `bkt` (avivsinai/bitbucket-cli) is gh-shaped, emits `--json`, and supports Cloud. Reads in the adapter and actions in the skills both go through `bkt`, keeping fn-73's rule "flowctl answers questions; skills act, using the forge's own CLI". [paraphrase]
- **Shared row mapping.** Bitbucket PR → shared row: `id`→`number`, `links.html.href`→`url`, `OPEN`→`OPEN`, `MERGED`→`MERGED`, `DECLINED` and `SUPERSEDED`→`CLOSED`, `source.branch.name`→`headRefName`, `source.commit.hash`→`headRefOid`, `destination.branch.name`→`baseRefName`. `mergedAt` is unknown in this spec (see Edge Cases); spec 3 supplies it. [inferred]
- **Branch lookup.** `bkt pr list` has no source-branch filter; the adapter lists by branch through `bkt api` on the pull-requests endpoint with a `source.branch.name` query. With a `q` filter Bitbucket ignores the `state` parameter (measured), so the states are part of the query. [inferred]
- **Workspace and repo come from the origin.** The adapter names them in every call. `bkt` itself answers only through a context (measured: with none, every command fails `no active context`), so an active Bitbucket Cloud context is part of `bkt`'s setup, checked by make-pr's preflight. [inferred]
- **make-pr dispatches by forge name.** make-pr reads `forge-bitbucket.md` for a Bitbucket origin, with a helper beside the GitLab one; GitHub and GitLab paths are not edited. [paraphrase]

## API Contracts
<!-- scope: technical -->

- Internal only. `list_prs` returns shared rows or a probe failure; a failed, unauthenticated or truncated read is a probe failure, never an empty list.
- `flowctl pilot snapshot` reports `forge: "bitbucket"` for a Bitbucket origin; no other output shape changes.
- Record live before relying: PR list by source branch (all states and open, with pagination), PR view, PR create (draft and ready), PR edit (title, description), PR publish (draft → ready), the answer for a branch with no PR, and `bkt auth status` logged in and logged out. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A second create for the same source and target branches rewrites the open pull request's title and description instead of failing (measured), so make-pr creates only after its existing-PR check. [inferred]
- HTTPS, SSH and SSH-alias origins all resolve; an SSH alias resolves through the existing `ssh -G` path. [inferred]
- Bitbucket returns short commit hashes; `headRefOid` is resolved to the full sha from the local clone when the commit is there, and a hash that cannot be resolved must not read as a different head. [inferred]
- Bitbucket has no merge timestamp on the PR; `updated_on` moves with every later comment and must never be reported as `mergedAt`. [paraphrase]
- PRs from forks share branch names; only PRs whose source repository is the origin repository count. [inferred]
- Bitbucket paginates; a listing that cannot prove it is complete is a probe failure. [inferred]
- A missing or unauthenticated `bkt`, or one without an active Bitbucket Cloud context, on a Bitbucket origin stops make-pr before any spec close or push, naming `bkt auth login https://bitbucket.org --kind cloud --web` and `bkt context create`. [inferred]
- make-pr never adds reviewers on Bitbucket unless the user asks (no `--with-default-reviewers`). [paraphrase]
- Live recording happens on a real Bitbucket Cloud repository with PRs that target a throwaway base branch and carry no reviewers, so nothing reaches a real default branch or notifies anyone. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A Bitbucket Cloud origin (HTTPS, SSH, or SSH alias for `bitbucket.org`) resolves to forge `bitbucket`, and `flowctl pilot snapshot` reports `forge: "bitbucket"`. Errors: an unparseable or non-Bitbucket origin keeps today's resolution; GitHub and GitLab origins resolve exactly as before. [inferred]
- **R2:** On a Bitbucket origin, the route judge and the pilot snapshot read the spec branch's PRs through `bkt` as shared rows, so a branch with no PR reports `pr_exists: false` and a branch with a PR reports it with number, url, state, head branch and head sha. Errors: `bkt` missing, unauthenticated, failing, or returning an incomplete listing → probe failure (`pr_probe_failed`), never "no PR". [paraphrase]
- **R3:** `flow --auto` on a Bitbucket Cloud origin runs from a ready spec through work and its reviews to an open draft PR on Bitbucket, with no `gh` stand-in on PATH. [strategy:Autonomous mode] Errors: a stop before the PR names the step and the reason, as on GitHub. [paraphrase]
- **R4:** make-pr on a Bitbucket origin creates the PR through `bkt` (draft or ready as make-pr decides today), updates title and description on a re-run, and marks a draft ready when asked, following `forge-bitbucket.md`. Errors: missing or unauthenticated `bkt` → stop before any spec close or push, naming the `bkt auth login` command; a PR-create failure → make-pr's existing failure path, nothing claimed as created. [inferred]
- **R5:** GitHub and GitLab behaviour and their tests are unchanged. No error surface beyond R1–R4. [paraphrase]
- **R6:** Each `bkt` command this spec relies on is first run against a live Bitbucket Cloud repository and its real output saved as a test fixture; tests with a stubbed `bkt` built from those fixtures cover R1, R2 and R4 in CI. [inferred]

## Boundaries
<!-- scope: business -->

- No resolve-pr or land here; those are the next two specs.
- No Bitbucket Data Center: `bkt` supports it, but the API shapes differ and it cannot be tested here. The adapter must not preclude adding it later. [paraphrase]
- No Bitbucket Issues as a tracker (Atlassian removed Cloud Issues in August 2026). [inferred]
- No new public flowctl verb, no config key.
- flow-next never stores or handles a Bitbucket token; authentication is `bkt`'s. [inferred]

## Decision Context
<!-- scope: both -->

Siblings: spec 2 (resolve-pr over Bitbucket PR comments) and spec 3 (land and merge evidence over Bitbucket), both from issue #602 and depending on this one.

**Why `bkt` over the alternatives.** Researched in the conversation: `curl` against the REST API in skill references would mean long, error-prone shell and token handling in every call, and diverges from the "forge's own CLI" pattern. flowctl performing the writes would need a public flowctl surface and break fn-73's split. Atlassian's Teamwork Graph CLI (`twg`) has PR commands but is explicitly beta with commands still changing. `bkt` is MIT, released roughly weekly (v0.38.1, 2026-11-09), in Homebrew core, WinGet and Scoop with signed binaries for macOS, Linux and Windows, and has a stable JSON contract. Risks: pre-1.0 and mostly one maintainer; the live-recorded fixtures (R6) catch command drift. [paraphrase]

**Why the stand-in is not the answer.** It worked only for `gh pr list`, depended on a personal keychain entry, reported `updated_on` as the merge time, a display name as the merger, and only approvals as reviews. [paraphrase]

**Why make-pr is in this spec.** Without it `flow --auto` still ends on `NEEDS_HUMAN`, only one stage later; fn-73 bundled make-pr with the adapter for the same reason. [paraphrase]

**Amended 2026-11-13 during work.** The adapter first claimed `bitbucket.org` through `owns_host` and avoided `bkt` contexts. Live runs showed `bkt` answers only through an active context and that Bitbucket Cloud's hosts are fixed, so the hosts are claimed directly and the context is a preflight-checked setup step; the `q`-ignores-`state` and create-rewrites findings were added to the constraints. [paraphrase]
