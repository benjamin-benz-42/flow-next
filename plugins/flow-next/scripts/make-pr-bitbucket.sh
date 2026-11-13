#!/usr/bin/env bash
# make-pr's pull requests on a Bitbucket Cloud origin. make-pr-preflight.sh runs this in
# place of gh for the same argv (`pr list --head <branch> --state all --json <keys>
# [--jq <expr>]`, `pr view --json <keys>`) and gets gh's JSON keys back: number,
# url, state (OPEN, MERGED, CLOSED) and baseRefName, whatever --json names.
# make-pr-create.sh runs `pr create` with gh's argv (`--title --body-file [--draft]
# --base --head`) and `pr edit <number> --body-file <file> [--ready]`; both print
# the pull request's URL.
# `auth-check` exits 0 when bkt is logged in to Bitbucket Cloud with an active Cloud context.
# Environment: ORIGIN_PROJECT (origin workspace/repo).
# Exit 0 is a complete answer; a failed, partial or malformed read exits nonzero,
# never an empty "no pull request".
set -euo pipefail
# Windows jq.exe ends lines with CRLF; drop the CR so counts and values compare equal (#541).
jq() { command jq "$@" | tr -d '\r'; return "${PIPESTATUS[0]}"; }
fail() { echo "make-pr-bitbucket.sh: $*" >&2; exit 1; }

if [[ "${1:-}" == auth-check ]]; then
  # bkt answers only through a context; a Cloud one names api.bitbucket.org.
  CONTEXTS=$(bkt context list --json 2>/dev/null) || fail "bkt context list failed"
  printf '%s' "$CONTEXTS" | jq -e '.active_context as $a | any(.contexts[]?; .name == $a and (.host | test("(^|//)api\\.bitbucket\\.org(/|$)")))' >/dev/null \
    || fail "no active bkt context for Bitbucket Cloud"
  bkt auth status >/dev/null 2>&1 || fail "bkt is not logged in"
  exit 0
fi

[[ "${1:-}" == pr && "${2:-}" =~ ^(list|view|create|edit)$ ]] || { echo "usage: make-pr-bitbucket.sh pr list|view|create|edit ... | auth-check" >&2; exit 2; }
[[ "${ORIGIN_PROJECT:-}" =~ ^[^/[:space:]\"]+/[^/[:space:]\"]+$ ]] || fail "no origin workspace/repo"
WORKSPACE=${ORIGIN_PROJECT%/*}; REPO=${ORIGIN_PROJECT#*/}

if [[ "$2" == create ]]; then
  shift 2; TITLE=""; BODY_FILE=""; BASE=""; HEAD=""; DRAFT=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title) TITLE=$2 ;; --body-file) BODY_FILE=$2 ;; --base) BASE=$2 ;; --head) HEAD=$2 ;;
      --draft) DRAFT=(--draft); shift; continue ;;
      *) echo "make-pr-bitbucket.sh: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift 2
  done
  [[ -n "$TITLE" && -f "$BODY_FILE" && -n "$BASE" && -n "$HEAD" ]] || fail "pr create needs --title, --body-file, --base and --head"
  # Bitbucket answers a second create for the same branches by rewriting the open pull
  # request, so make-pr's existing-PR check runs first. No reviewers are added.
  OUT=$(bkt pr create --title "$TITLE" --description "$(<"$BODY_FILE")" --source "$HEAD" --target "$BASE" \
          ${DRAFT[@]+"${DRAFT[@]}"} --workspace "$WORKSPACE" --repo "$REPO" --json) \
    || { printf '%s\n' "${OUT:-}" >&2; fail "bkt pr create failed"; }
  printf '%s' "$OUT" | jq -er '.url | select(type == "string" and . != "")' || fail "no pull request URL in bkt's answer"
  exit 0
fi

if [[ "$2" == edit ]]; then
  NUMBER=${3:-}; shift 3; BODY_FILE=""; READY=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --body-file) BODY_FILE=$2; shift ;;
      --ready) READY=1 ;;
      *) echo "make-pr-bitbucket.sh: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift
  done
  [[ "$NUMBER" =~ ^[0-9]+$ && -f "$BODY_FILE" ]] || fail "pr edit needs a pull request number and --body-file"
  # The draft state stays as it is unless --ready publishes the draft.
  OUT=$(bkt pr edit "$NUMBER" --description "$(<"$BODY_FILE")" --workspace "$WORKSPACE" --repo "$REPO" --json) \
    || fail "bkt pr edit $NUMBER failed"
  URL=$(printf '%s' "$OUT" | jq -er '.pull_request.links.html.href | select(type == "string" and . != "")') \
    || fail "no pull request URL in bkt's answer"
  if [[ -n "$READY" ]]; then
    bkt pr publish "$NUMBER" --workspace "$WORKSPACE" --repo "$REPO" >/dev/null || fail "bkt pr publish $NUMBER failed"
  fi
  printf '%s\n' "$URL"
  exit 0
fi

READ=$2; shift 2
HEAD=""; FILTER="."
while [[ $# -gt 0 ]]; do
  case "$1" in
    --head) HEAD=$2 ;;
    --state) [[ "$2" == all ]] || fail "only --state all is supported" ;;
    --json) ;;   # every read answers the same keys
    --jq) FILTER=$2 ;;
    *) echo "make-pr-bitbucket.sh: unsupported argument $1" >&2; exit 2 ;;
  esac
  shift 2
done
[[ "$READ" == list ]] || HEAD=$(git branch --show-current)
[[ -n "$HEAD" ]] || fail "no branch to read"
[[ "$HEAD" != *'"'* && "$HEAD" != *'\'* ]] || fail "unsupported branch name $HEAD"
# With a `q` filter Bitbucket ignores the `state` parameter, so the states go into the query.
# A fork's pull request can share the branch name; only the origin repository's count.
QUERY="source.repository.full_name=\"$ORIGIN_PROJECT\" AND source.branch.name=\"$HEAD\" AND (state=\"OPEN\" OR state=\"MERGED\" OR state=\"DECLINED\" OR state=\"SUPERSEDED\")"
ROWS='[]'; PAGE=1
while :; do
  LISTED=$(bkt api "/repositories/$ORIGIN_PROJECT/pullrequests" -P "q=$QUERY" -P pagelen=50 -P "page=$PAGE") \
    || fail "bkt api pullrequests failed"
  # Exactly one JSON page: empty or other output is unreadable, never an empty listing.
  printf '%s' "$LISTED" | jq -se 'length == 1 and (.[0].values | type) == "array"' >/dev/null \
    || fail "unreadable pull-request listing"
  ROWS=$(printf '%s\n%s' "$ROWS" "$LISTED" | jq -cs '.[0] + .[1].values')
  printf '%s' "$LISTED" | jq -e '.next | type == "string"' >/dev/null || break
  PAGE=$((PAGE + 1))
done
printf '%s' "$ROWS" | jq -c --arg read "$READ" '
  if all(.[]; type == "object" and (.id | type) == "number" and (.links.html.href | type) == "string"
         and (.state | IN("OPEN", "MERGED", "DECLINED", "SUPERSEDED"))
         and (.destination.branch.name | type) == "string")
  then [.[] | {number: .id, url: .links.html.href, baseRefName: .destination.branch.name,
               state: {OPEN: "OPEN", MERGED: "MERGED", DECLINED: "CLOSED", SUPERSEDED: "CLOSED"}[.state]}]
       | if $read == "view" then map(select(.state == "OPEN"))[0] // empty else . end
  else error("malformed pull-request row") end' | jq -rc "$FILTER" \
  || fail "malformed pull-request listing"
