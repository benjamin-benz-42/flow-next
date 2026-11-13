---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-321-forge-adapter-and-make-pr-over.1 Implement Forge adapter and make-pr over Bitbucket Cloud pull requests

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Bitbucket Cloud joins the forge registry: bitbucket.org, ssh.bitbucket.org and altssh.bitbucket.org origins resolve to `bitbucket`, and `list_prs` reads pull requests through `bkt api` (states inside `q`, fork rows excluded, short hashes expanded, incomplete or malformed pages fail closed). make-pr detects the forge in preflight, checks bkt and its Cloud context, and opens/updates/publishes pull requests through `make-pr-bitbucket.sh` behind PR_READ; the codex installer ships the helper. Fixtures are sanitized live recordings from a sandbox pull request.

Live: pilot snapshot on a Bitbucket repo reports forge bitbucket, probe_failed false; make-pr's preflight+create closed a sandbox spec, pushed and opened draft PR, route then existing_pr_tail; --update --ready replaced the body and published.

stage: impl-review - ran (codex, gpt-6.1-sol): NEEDS_WORK (6 findings; 5 fixed, #2 update-title declined: GitHub and GitLab update only the body too) -> re-review SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: d00b601bf8a86949a4201829edbffa37c41a9a43, c91cb65df6d87f9fdd73e69924a4592bd11c2f58
- Tests: python3 -m pytest -q tests/test_forge.py tests/test_make_pr_bitbucket.py tests/test_codex_config_merge.py tests/test_make_pr_gitlab.py (+17 related files, 255 passed)
- PRs: