# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when the origin's forge is `bitbucket`. The gates, their order, the
> verdicts and the terminal line stay as workflow.md says; only these reads and calls change.

`bkt` names the repository explicitly: first
`export ORIGIN_PROJECT="$(git remote get-url origin | sed -E 's#^(https?|ssh|git\+ssh)://[^/]+/##; s#^[^@/]+@[^:]+:##; s#\.git$##; s#/$##')"`
and use `--workspace "${ORIGIN_PROJECT%%/*}" --repo "${ORIGIN_PROJECT#*/}"` (`$WR` below). `$PR` is
the pull request id, `$HEAD_SHA` the full head SHA and `$BRANCH` the source branch.

- **Read the pull request.** `bkt api "/repositories/$ORIGIN_PROJECT/pullrequests/$PR"`: `state`
  (`OPEN`, `MERGED`, `DECLINED` and `SUPERSEDED`, the last two closed unmerged), `draft`,
  `source.branch.name`, `source.repository.full_name`, `source.commit.hash`,
  `destination.branch.name`, `links.html.href`, and once merged `merge_commit.hash`. Bitbucket
  abbreviates hashes: expand one with `git rev-parse "<hash>^{commit}"` after the fetch below, or
  `bkt api "/repositories/$ORIGIN_PROJECT/commit/<hash>" | jq -r .hash`; a shortened SHA is never
  used for a gate.
- **Specs at the head.** Bitbucket Cloud publishes no pull-request head refs: fetch the source
  branch (`git fetch origin "refs/heads/$BRANCH"`, or from the source repository when
  `source.repository.full_name` differs from `ORIGIN_PROJECT`) and check that `FETCH_HEAD` is
  `$HEAD_SHA`, else the head moved: read again. Read `.flow/specs/*.json` and `.flow/tasks/` with
  `git ls-tree` and `git show "$HEAD_SHA:<path>"`, and the base from `origin/<destination branch>`, in
  place of the trees API. The selection rules are unchanged.
- **Readiness.** For the selected spec, run `"$FLOWCTL" pilot snapshot --spec <spec-id> --json` in
  a detached worktree at `$HEAD_SHA` (the one repairs use). Its `.selected.pr.open` `url` must be
  this pull request's `links.html.href` and `readiness.head_sha` the head you read. A moved head means
  read again (`RESOLVING` if it keeps moving); at an unchanged head with no match (a fork's pull
  request, which the snapshot does not list, or a spec whose `branch_name` names another branch)
  stop `NEEDS_HUMAN`. `readiness` holds `mergeable` and `merge_state` (Bitbucket's merge checks, as
  `bkt pr mergeability` reports them), `builds` (the worst build status on this head, null when
  none is reported), `approval` (`approved`, `changes_requested` or `none`), `draft`, `green` and
  `ready`. A pull request without a spec has no readiness read: stop `NEEDS_HUMAN`.
- **Conflicts and catch-up.** `mergeable: CONFLICTING` stops `BLOCKED` naming the branch;
  `UNKNOWN` is `RESOLVING`. Bitbucket merges a branch that is behind its base, so there is no
  catch-up.
- **Threads.** Open comment threads go to resolve-pr exactly as on GitHub, from the detached worktree
  at `$HEAD_SHA`; its Bitbucket reference fetches and resolves them and pushes to `$BRANCH`.
- **Builds.** `SUCCESSFUL` is green, and no build reported is nothing to wait for; a build the
  repository requires blocks in `merge_state` instead. `INPROGRESS` is a pending check. `FAILED` or
  `STOPPED` stops `BLOCKED` naming each failing build with its `url` from
  `bkt api "/repositories/$ORIGIN_PROJECT/pullrequests/$PR/statuses"`: land does not repair or rerun
  Bitbucket builds.
- **Review.** `approval: changes_requested` stops `AWAITING_REVIEW`. `merge_state: BLOCKED` names
  its cause in `bkt pr mergeability $PR $WR --json` (`checks` with `blocking: true`): a missing
  approval stops `AWAITING_REVIEW`, any other check `NEEDS_HUMAN` naming it. Land merges only on
  `ready: true`.
- **Patience.** The last authored push is the head commit's `date` from
  `bkt api "/repositories/$ORIGIN_PROJECT/commit/$HEAD_SHA"`.
- **Merge one layer.** An open pull request targeting `$BRANCH`
  (`bkt api "/repositories/$ORIGIN_PROJECT/pullrequests" -P "q=destination.branch.name=\"$BRANCH\" AND state=\"OPEN\""`)
  or a draft stops `NEEDS_HUMAN`. Bitbucket's merge takes no expected head, so with a fresh
  `ready: true` read the pull request once more right before merging and stop `RESOLVING` when
  `source.commit.hash` no longer names `$HEAD_SHA`. Then
  `bkt pr merge $PR --strategy squash --message "<title> (#$PR)" $WR`. A refused squash (the
  repository forbids it) stops `NEEDS_HUMAN`; land never picks another strategy. Then read the pull
  request again: only `state: MERGED` with a `merge_commit` confirms `MERGED`, and only when its
  `source.commit.hash` still names `$HEAD_SHA`; a merge of another head stops `NEEDS_HUMAN` naming
  both, with the merge commit.

The GitHub-only steps (merge queue, rulesets, `update-branch`, rerunning failed checks, stacks and
marking a draft ready) have no Bitbucket arm: where land needs one, it stops `NEEDS_HUMAN`. After the
merge, the tracker touchpoint runs as on GitHub; flowctl reads the merged pull request as merge
evidence.
