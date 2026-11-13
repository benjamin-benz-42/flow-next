"""land on a Bitbucket Cloud origin: the answers its forge reference reads.

bkt answers replay live recordings from Bitbucket Cloud sandbox pull request 30, squash-merged
into a throwaway base, and open pull request 29 (fixtures/bitbucket/; workspace, repository and
people renamed). The readiness read itself is covered in test_forge.BitbucketLandReadTests.
"""
import json
import unittest

from test_make_pr_bitbucket import BitbucketShellCase, answers, recorded

WR = ["--workspace", "flownext", "--repo", "flownext"]


class ReferenceReadTests(BitbucketShellCase):
    def bkt(self, argv, *fixtures):
        result = self.run_sh(["bkt", *argv], BKT_ANSWERS=answers(*fixtures))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_a_confirmed_merge_names_the_gated_head_and_a_merge_commit(self):
        open_pr = json.loads(self.bkt(["api", "/repositories/flownext/flownext/pullrequests/29"], recorded("pr-detail-open")))
        self.assertEqual((open_pr["state"], open_pr["draft"]), ("OPEN", False))
        merged = json.loads(self.bkt(["api", "/repositories/flownext/flownext/pullrequests/30"], recorded("pr-detail-merged")))
        self.assertEqual(merged["state"], "MERGED")
        self.assertTrue(merged["merge_commit"]["hash"])
        # The merged source commit is the head land gated: the recorded listing before the merge.
        listed = json.loads(json.loads(recorded("pr-branch-merged").read_text(encoding="utf-8"))["stdout"])
        self.assertEqual(merged["source"]["commit"]["hash"], listed["values"][0]["source"]["commit"]["hash"])

    def test_the_merge_call_and_the_reads_around_it(self):
        out = self.bkt(["pr", "merge", "30", "--strategy", "squash", "--message",
                        "test: flow-next Bitbucket adapter E2E sandbox (#30)", *WR], recorded("pr-merge"))
        self.assertIn("Merged pull request #30", out)
        checks = json.loads(self.bkt(["pr", "mergeability", "30", *WR, "--json"], recorded("pr-mergeability-merged")))
        self.assertEqual([c["type"] for c in checks["checks"] if c["blocking"]], ["pullrequest_state_check"])
        children = json.loads(self.bkt(["api", "/repositories/flownext/flownext/pullrequests", "-P",
                                        'q=destination.branch.name="fn-bb-test/pr-1" AND state="OPEN"'],
                                       recorded("pr-children-none")))
        self.assertEqual(children["values"], [])
        commit = json.loads(self.bkt(["api", "/repositories/flownext/flownext/commit/3851dad1ef84"],
                                     recorded("commit-merged-head")))
        self.assertTrue(commit["date"])


if __name__ == "__main__":
    unittest.main()
