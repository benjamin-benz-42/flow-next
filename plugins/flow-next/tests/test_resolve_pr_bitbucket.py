"""resolve-pr on a Bitbucket Cloud origin: the pull-request comment scripts.

bkt answers replay live recordings from Bitbucket Cloud sandbox pull request 30
(fixtures/bitbucket/: a general comment resolved, an inline comment made outdated by a
later push and answered twice, then replied to and resolved; workspace, repository and
people renamed).
"""
import json
import shutil
import unittest
from pathlib import Path

from test_make_pr_bitbucket import BitbucketShellCase, answers, recorded

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "skills" / "flow-next-resolve-pr" / "scripts"
INLINE, GENERAL = 901666329, 901666326


class CommentCase(BitbucketShellCase):
    def setUp(self):
        super().setUp()
        (self.bin / "cat").symlink_to(shutil.which("cat"))   # the reply script reads stdin with cat

    def fetch(self, *fixtures):
        return self.run_sh(["bash", str(SCRIPTS / "get-bitbucket-comments"), "30"], BKT_ANSWERS=answers(*fixtures))


class FetchTests(CommentCase):
    def test_unresolved_threads_carry_replies_and_bitbuckets_outdated_flag(self):
        result = self.fetch(recorded("comments-open"), recorded("comment-inline-outdated"))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["pr_number"], 30)
        self.assertEqual([t["id"] for t in out["review_threads"]], [INLINE])
        thread = out["review_threads"][0]
        self.assertEqual((thread["isOutdated"], thread["path"], thread["line"]), (True, ".fn-bb-test/README2", 1))
        self.assertEqual([c["body"] for c in thread["comments"]],
                         ["Inline sandbox comment: typo here.", "Fixed in the next commit.", "Reply via the flow-next script."])
        self.assertEqual(set(thread["comments"][0]), {"id", "author", "body", "createdAt"})
        self.assertEqual((out["pr_comments"], out["review_bodies"]), ([], []))
        self.assertEqual(out["cross_invocation"], {
            "signal": True, "resolved_threads": [{"id": GENERAL, "path": None, "line": None}]})

    def test_resolved_threads_are_not_fetched_again(self):
        result = self.fetch(recorded("comments-resolved"))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["review_threads"], [])
        self.assertEqual([t["id"] for t in out["cross_invocation"]["resolved_threads"]], [GENERAL, INLINE])

    def test_deleted_and_pending_comments_are_not_feedback(self):
        def change(page):
            values = page["values"]
            values[0].update(resolution=None, deleted=True)   # the general comment, deleted
            values[1].update(pending=True)                     # the inline comment, a draft
            return page
        result = self.fetch(self.as_bkt("comments-open", change))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["review_threads"], [])

    def test_failed_or_malformed_reads_exit_nonzero(self):
        cases = {
            "no bkt context": [self.as_bkt("comments-open", returncode=1, stdout="",
                                           stderr="Error: no active context; run `bkt context use <name>`\n")],
            "empty output": [self.as_bkt("comments-open", stdout="")],
            "size says comments are missing": [self.as_bkt("comments-open", lambda p: {**p, "size": 99})],
            "row without id": [self.as_bkt("comments-open", lambda p: {**p, "values": [{"deleted": False}]})],
            "detail read fails": [recorded("comments-open"), self.as_bkt("comment-inline-outdated", returncode=1, stdout="")],
        }
        for name, fixtures in cases.items():
            with self.subTest(name):
                result = self.fetch(*fixtures)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout, "")


class ReplyResolveTests(CommentCase):
    def test_reply_is_threaded_under_the_comment_then_resolves(self):
        reply = self.run_sh(["bash", "-c", f'printf "Fixed in the recorded commit." | bash "{SCRIPTS / "reply-to-bitbucket-comment"}" 30 {INLINE}'],
                            BKT_ANSWERS=answers(recorded("comment-reply")))
        self.assertEqual(reply.returncode, 0, reply.stderr)
        resolve = self.run_sh(["bash", str(SCRIPTS / "resolve-bitbucket-comment"), "30", str(INLINE)],
                              BKT_ANSWERS=answers(recorded("comment-resolve")))
        self.assertEqual(resolve.returncode, 0, resolve.stderr)
        self.assertEqual([call[1:5] for call in self.bkt_calls()],
                         [["pr", "comment", "30", "--parent"], ["pr", "comments", "resolve", "30"]])

    def test_resolving_twice_succeeds(self):
        again = self.run_sh(["bash", str(SCRIPTS / "resolve-bitbucket-comment"), "30", str(INLINE)],
                            BKT_ANSWERS=answers(recorded("comment-resolve-again")))
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("already resolved", again.stdout)

    def test_empty_reply_never_reaches_bkt(self):
        empty = self.run_sh(["bash", "-c", f'printf "" | bash "{SCRIPTS / "reply-to-bitbucket-comment"}" 30 {INLINE}'])
        self.assertEqual(empty.returncode, 1)
        self.assertEqual(self.bkt_calls(), [])

    def test_failed_reply_or_resolve_exits_nonzero(self):
        failed = self.as_bkt("comment-resolve", returncode=1, stdout="", stderr="Error: 403 Forbidden\n")
        result = self.run_sh(["bash", str(SCRIPTS / "resolve-bitbucket-comment"), "30", str(INLINE)],
                             BKT_ANSWERS=answers(failed))
        self.assertEqual(result.returncode, 1)
        self.assertIn("403", result.stderr)


if __name__ == "__main__":
    unittest.main()
