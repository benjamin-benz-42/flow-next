# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when preflight sets `FORGE=bitbucket`.

Preflight has checked that `bkt` is installed, logged in, and has an active Bitbucket Cloud context,
and set `FORGE`, `PR_READ` (the bundled `make-pr-bitbucket.sh`) and `ORIGIN_PROJECT` (the
`workspace/repo` path). Carry all three into the create call, with `ORIGIN_PROJECT` exported, as you
carry `BASE_REF`. `make-pr-create.sh` then pushes and opens or updates the pull request through
`PR_READ` in place of gh, with the same body, draft rules and close as on GitHub. An explicit
`FLOW_PR_CREATE_CMD` still wins over the helper for creation.

- A draft is Bitbucket's own draft flag. `--update` replaces the description and keeps the draft
  state; `--update --ready` publishes the draft.
- No reviewers are added; the person adds them.
- A second create for the same source and target branches rewrites the open pull request instead of
  failing, so never create past preflight's existing-PR check.
- There is no stack link: while a parent's pull request is open, the child targets its branch.
- Tracker finalize: the pull request's `created_on` is the `<PR-createdAt>`:
  `bkt pr view "${PR_URL##*/}" --workspace "${ORIGIN_PROJECT%%/*}" --repo "${ORIGIN_PROJECT#*/}" --json | jq -r .pull_request.created_on`.
- No-spec path: preflight stops there before its existing-PR check, so first read
  `"$PR_READ" pr view --json number --jq .number`; an open pull request means `--update`, never a
  create. Otherwise follow no-spec-path.md with `"$PR_READ" pr create --title <title> --body-file <file>
  [--draft] --base <branch> --head <branch>` in place of `gh pr create`. `--base` is required; without
  `--base`, use the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD` minus
  `origin/`). Under `--update`, run `"$PR_READ" pr edit <number> --body-file <file>`, with the number
  from `"$PR_READ" pr view --json number --jq .number`.
