"""make-pr on a Bitbucket Cloud origin: the shell forge rule and the pull-request helper.

bkt answers replay live recordings from a Bitbucket Cloud sandbox pull request
(fixtures/bitbucket/: argv, exit code, raw stdout and stderr; workspace,
repository and people renamed).
"""
import json
import os
import sys
import unittest
from pathlib import Path

from test_make_pr_gitlab import GitLabShellCase

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
PREFLIGHT = SCRIPTS / "make-pr-preflight.sh"
HELPER = SCRIPTS / "make-pr-bitbucket.sh"
FIXTURES = TESTS / "fixtures" / "bitbucket"
PROJECT = "flownext/flownext"
PR_URL = "https://bitbucket.org/flownext/flownext/pull-requests/29"

BKT_STUB = f'''#!{sys.executable}
import json, os, sys
argv = ["bkt", *sys.argv[1:]]
with open(os.environ["STUB_CALLS"], "a") as log:
    log.write(json.dumps(argv) + "\\n")
for path in os.environ.get("BKT_ANSWERS", "").split(os.pathsep):
    if path:
        fx = json.load(open(path, encoding="utf-8"))
        if fx["argv"] == argv:
            sys.stdout.write(fx["stdout"]); sys.stderr.write(fx["stderr"]); sys.exit(fx["returncode"])
sys.exit("stub: no recorded bkt answer for " + repr(argv))
'''


def recorded(name: str) -> Path:
    return FIXTURES / f"{name}.json"


def answers(*paths: Path) -> str:
    return os.pathsep.join(str(p) for p in paths)


class BitbucketShellCase(GitLabShellCase):
    def setUp(self):
        super().setUp()
        self.stub("bkt", BKT_STUB)

    def run_sh(self, argv, cwd=None, **env):
        return super().run_sh(argv, cwd=cwd, **{"ORIGIN_PROJECT": PROJECT, **env})

    def bkt_calls(self):
        return [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()
                if line.startswith("[")]

    def as_bkt(self, name, change=None, **fields):
        """A recorded answer, optionally with its parsed stdout changed or fields replaced."""
        fx = json.loads(recorded(name).read_text(encoding="utf-8"))
        if change:
            fx["stdout"] = json.dumps(change(json.loads(fx["stdout"])))
        fx.update(fields)
        path = self.tmp / f"{name}-{len(list(self.tmp.glob('*.json')))}.json"
        path.write_text(json.dumps(fx), encoding="utf-8")
        return path


class HelperReadTests(BitbucketShellCase):
    LIST = [str(HELPER), "pr", "list", "--state", "all", "--json", "number,state,baseRefName", "--head"]

    def test_listing_answers_in_gh_keys(self):
        listed = self.run_sh([*self.LIST, "fn-bb-test/pr-1"], BKT_ANSWERS=answers(recorded("pr-branch-open")))
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(json.loads(listed.stdout), [
            {"number": 29, "url": PR_URL, "baseRefName": "fn-bb-test/sandbox-base", "state": "OPEN"}])
        none = self.run_sh([*self.LIST, "fn-bb-test/none"], BKT_ANSWERS=answers(recorded("pr-branch-none")))
        self.assertEqual((none.returncode, none.stdout.strip()), (0, "[]"), none.stderr)

    def test_view_answers_the_branch_open_pull_request(self):
        repo = self.repo_on("fn-bb-test/pr-1")
        view = self.run_sh([str(HELPER), "pr", "view", "--json", "number,state", "--jq", 'select(.state=="OPEN") | .number'],
                           cwd=repo, BKT_ANSWERS=answers(recorded("pr-branch-open")))
        self.assertEqual((view.returncode, view.stdout.strip()), (0, "29"), view.stderr)
        merged = self.as_bkt("pr-branch-open", lambda p: {**p, "values": [{**p["values"][0], "state": "MERGED"}]})
        none = self.run_sh([str(HELPER), "pr", "view", "--json", "url,state,number"], cwd=repo, BKT_ANSWERS=answers(merged))
        self.assertEqual((none.returncode, none.stdout.strip()), (0, ""), none.stderr)

    def test_failed_or_malformed_reads_exit_nonzero(self):
        cases = {
            "no bkt context": self.as_bkt("pr-branch-no-context"),
            "empty output": self.as_bkt("pr-branch-open", stdout=""),
            "unknown state": self.as_bkt("pr-branch-open", lambda p: {**p, "values": [{**p["values"][0], "state": "OPENED"}]}),
            "no values": self.as_bkt("pr-branch-open", lambda p: {k: v for k, v in p.items() if k != "values"}),
            "size says rows are missing": self.as_bkt("pr-branch-open", lambda p: {**p, "values": [], "size": 1}),
        }
        for name, path in cases.items():
            with self.subTest(name):
                result = self.run_sh([*self.LIST, "fn-bb-test/pr-1"], BKT_ANSWERS=answers(path))
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout, "")

    def test_auth_check(self):
        ok = self.run_sh([str(HELPER), "auth-check"], BKT_ANSWERS=answers(recorded("context-list"), recorded("auth-status")))
        self.assertEqual(ok.returncode, 0, ok.stderr)
        none = self.run_sh([str(HELPER), "auth-check"], BKT_ANSWERS=answers(recorded("context-list-none"), recorded("auth-status")))
        self.assertEqual(none.returncode, 1)
        self.assertIn("no active bkt context for Bitbucket Cloud", none.stderr)


class HelperWriteTests(BitbucketShellCase):
    def test_create_passes_draft_and_body_and_prints_the_url(self):
        body = self.body_file("Sandbox PR for the flow-next Bitbucket adapter. Safe to decline.")
        result = self.run_sh([str(HELPER), "pr", "create", "--title", "test: flow-next Bitbucket adapter sandbox",
                              "--body-file", str(body), "--draft", "--base", "fn-bb-test/sandbox-base",
                              "--head", "fn-bb-test/pr-1"], BKT_ANSWERS=answers(recorded("pr-create-draft")))
        self.assertEqual((result.returncode, result.stdout.strip()), (0, PR_URL), result.stderr)
        self.assertNotIn("--with-default-reviewers", self.bkt_calls()[0])

    def test_ready_create_passes_no_draft_flag(self):
        body = self.body_file("Conflict sandbox PR. Safe to decline.")
        result = self.run_sh([str(HELPER), "pr", "create", "--title", "test: flow-next Bitbucket conflict sandbox",
                              "--body-file", str(body), "--base", "fn-bb-test/sandbox-base", "--head", "fn-bb-test/pr-4"],
                             BKT_ANSWERS=answers(recorded("pr-create-ready")))
        self.assertEqual((result.returncode, result.stdout.strip()),
                         (0, "https://bitbucket.org/flownext/flownext/pull-requests/33"), result.stderr)
        self.assertNotIn("--draft", self.bkt_calls()[0])

    def test_refused_create_fails_with_bitbuckets_answer(self):
        body = self.body_file("x")
        result = self.run_sh([str(HELPER), "pr", "create", "--title", "nobranch", "--body-file", str(body),
                              "--base", "fn-bb-test/sandbox-base", "--head", "fn-bb-test/does-not-exist"],
                             BKT_ANSWERS=answers(recorded("pr-create-no-branch")))
        self.assertEqual(result.returncode, 1)
        self.assertIn("branch not found", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_edit_replaces_the_description_and_publishes_only_when_ready(self):
        body = self.body_file("Updated sandbox body.")
        argv = [str(HELPER), "pr", "edit", "29", "--body-file", str(body)]
        keep = self.run_sh(argv, BKT_ANSWERS=answers(recorded("pr-edit")))
        self.assertEqual((keep.returncode, keep.stdout.strip()), (0, PR_URL), keep.stderr)
        self.assertEqual([call[1] for call in self.bkt_calls()], ["pr"])
        self.assertEqual([call[2] for call in self.bkt_calls()], ["edit"])
        self.calls.write_text("", encoding="utf-8")
        ready = self.run_sh([*argv, "--ready"], BKT_ANSWERS=answers(recorded("pr-edit"), recorded("pr-publish")))
        self.assertEqual((ready.returncode, ready.stdout.strip()), (0, PR_URL), ready.stderr)
        self.assertEqual([call[2] for call in self.bkt_calls()], ["edit", "publish"])


class OriginProjectTests(BitbucketShellCase):
    def test_every_supported_origin_form(self):
        for origin in ("https://bitbucket.org/flownext/flownext.git", "https://bitbucket.org/flownext/flownext.git/",
                       "https://user@bitbucket.org/flownext/flownext", "git@bitbucket.org:flownext/flownext.git",
                       "bitbucket.org:flownext/flownext.git", "bb-work:flownext/flownext.git",
                       "ssh://git@altssh.bitbucket.org:443/flownext/flownext.git"):
            with self.subTest(origin):
                result = self.run_sh([str(HELPER), "origin-project"], cwd=self.repo_on("main", origin))
                self.assertEqual((result.returncode, result.stdout.strip()), (0, PROJECT), result.stderr)
        bad = self.run_sh([str(HELPER), "origin-project"], cwd=self.repo_on("main", "https://bitbucket.org/flownext"))
        self.assertEqual(bad.returncode, 1)


class OriginBlockTests(BitbucketShellCase):
    """The origin block runs before any close or push (the `# end:block` seam, without flowctl)."""

    BLOCK = PREFLIGHT.read_text(encoding="utf-8").split("# end:block", 1)[0]
    REPORT = '\nprintf "FORGE=%s PR_READ=%s ORIGIN_PROJECT=%s" "$FORGE" "$PR_READ" "$ORIGIN_PROJECT"\n'

    def block(self, origin, *, report=True, dry_run="0", **env):
        repo = self.repo_on("main", origin)
        return self.run_sh(["bash", "-c", self.BLOCK + (self.REPORT if report else "")], cwd=repo,
                           REPO_ROOT=str(repo), DRY_RUN=dry_run, FLOWCTL=str(SCRIPTS / "flowctl"),
                           GITLAB_HOST="", ORIGIN_PROJECT="", **env)

    def test_bitbucket_origins_with_a_ready_bkt_pass(self):
        ready = answers(recorded("context-list"), recorded("auth-status"))
        for origin in ("git@bitbucket.org:flownext/flownext.git", "https://bitbucket.org/flownext/flownext.git",
                       "git@ssh.bitbucket.org:flownext/flownext.git", "https://BITBUCKET.ORG/flownext/flownext.git"):
            with self.subTest(origin):
                result = self.block(origin, BKT_ANSWERS=ready)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"FORGE=bitbucket PR_READ={HELPER} ORIGIN_PROJECT={PROJECT}")

    def test_missing_or_unready_bkt_stops_naming_the_setup(self):
        for name in ("missing", "no context"):
            with self.subTest(name):
                if name == "missing":
                    (self.bin / "bkt").rename(self.tmp / "bkt-away")
                result = self.block("git@bitbucket.org:flownext/flownext.git", report=False,
                                    BKT_ANSWERS=answers(recorded("context-list-none"), recorded("auth-status")))
                if name == "missing":
                    (self.tmp / "bkt-away").rename(self.bin / "bkt")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("bkt auth login https://bitbucket.org --kind cloud --web", result.stderr)

    def test_dry_run_names_the_forge_without_checks(self):
        result = self.block("git@bitbucket.org:flownext/flownext.git", dry_run="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"FORGE=bitbucket PR_READ={HELPER} ORIGIN_PROJECT={PROJECT}")
        self.assertEqual(self.bkt_calls(), [])


if __name__ == "__main__":
    unittest.main()
