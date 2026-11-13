# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when the Preamble reads `FORGE=bitbucket`. On Bitbucket Cloud every
> top-level comment, inline or general, is a resolvable thread, so every piece of feedback is a
> review thread here and there are no separate PR comments.

The phases, triage, dispatch, validation and verdicts are workflow.md's; only the commands below
change. The scripts and `bkt` name the repository explicitly, so first export it from the origin:
`export ORIGIN_PROJECT="$(git remote get-url origin | sed -E 's#^(https?|ssh|git\+ssh)://[^/]+/##; s#^[^@/]+@[^:]+:##; s#\.git$##; s#/$##')"`.

- **Preamble:** in place of the gh check, `bash "$(dirname "$FLOWCTL")/make-pr-bitbucket.sh" auth-check || { echo "bkt not ready. Run: bkt auth login https://bitbucket.org --kind cloud --web, then bkt context create cloud --host api.bitbucket.org --workspace ${ORIGIN_PROJECT%%/*} --set-active"; exit 1; }`.
- **Phase 0:** a number is the pull request id. A pull request URL
  (`https://bitbucket.org/<workspace>/<repo>/pull-requests/<id>`) gives its id and must name this
  checkout's repository: compare `<workspace>/<repo>`, ignoring case, with `ORIGIN_PROJECT`, and on a
  mismatch stop naming both, as for a GitHub URL. Comment URLs (targeted mode) are GitHub's: on
  Bitbucket, pass the id, the URL or nothing.
- **Phase 1:** with no target,
  `bash "$(dirname "$FLOWCTL")/make-pr-bitbucket.sh" pr view --json number --jq .number` reads the
  current branch's open pull request. Fetch with
  `FEEDBACK_JSON=$(bash "$SCRIPTS/get-bitbucket-comments" "$PR_NUMBER")`: the same keys as
  `get-pr-comments`, every page, with deleted and pending comments left out and each thread's
  replies as its comments. `pr_comments` and `review_bodies` are always empty, and `isOutdated` is
  Bitbucket's own flag for an inline comment whose line changed, so the resolver re-locates it by
  content.
- **Phase 5:** tell each resolver this is a Bitbucket pull request, and that where its instructions
  say `gh pr diff` or `gh pr view` it reads `git diff origin/<destination branch>...HEAD` and
  `bkt pr view <id> --workspace <workspace> --repo <repo> --json` instead.
- **Phase 7:** push to the pull request's source branch, read with that `bkt pr view` as
  `.pull_request.source.branch.name`. On the branch, `git push`; from a detached checkout,
  `git push origin "HEAD:<source branch>"`. When `.pull_request.source.repository.full_name`
  differs from `ORIGIN_PROJECT` (a fork), push to that repository: the origin URL with
  `ORIGIN_PROJECT` replaced by the source repository's `full_name`.
- **Phase 8:** as on GitHub, a thread gets its reply and then, unless the verdict is `needs-human`,
  is resolved:
  `echo "$REPLY" | bash "$SCRIPTS/reply-to-bitbucket-comment" "$PR_NUMBER" "$FB_ID"`, then
  `bash "$SCRIPTS/resolve-bitbucket-comment" "$PR_NUMBER" "$FB_ID"`. The reply is threaded under the
  top-level comment; never post it as a new top-level comment, which would open a new unresolved
  thread. Run each thread's pair on its own: a failed reply skips that thread's resolve, and a failed
  reply or resolve is reported for that thread while the run continues with the rest.
- **Phase 9:** re-fetch with `get-bitbucket-comments`.
- **Errors:** an HTTP 429 from bkt follows the rate-limit rule. Resolving an already resolved thread
  succeeds again; nothing to do.
