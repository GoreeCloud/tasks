"""Proposed native semantics, pure fixtures only, never edits a local DB."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import BackupError
from subtasks_recovery import plan_subtree_trash, plan_subtree_restore
from subtasks_contract import validate_proposed_graph

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/portable/schema4-proposed-synthetic.json"
WHEN = "2026-11-02T14:00:00Z"


class PreviewRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.original = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_full_three_level_group_roundtrip_is_lossless(self):
        original = deepcopy(self.original)
        planned = plan_subtree_trash(original, [], "task-notes", WHEN, "group-1")
        self.assertEqual(original, self.original)
        self.assertEqual(len(planned["workspace"]["tasks"]), 0)
        self.assertEqual(len(planned["trash"]), 3)
        self.assertTrue(all(e["groupSize"] == 3 for e in planned["trash"]))
        restored = plan_subtree_restore(planned["workspace"], planned["trash"], "group-1")
        self.assertEqual(restored["workspace"], self.original)
        self.assertEqual(restored["trash"], [])
        self.assertEqual(validate_proposed_graph(restored["workspace"])["depths"]["task-grandchild"], 3)

    def test_child_branch_does_not_delete_parent(self):
        planned = plan_subtree_trash(self.original, [], "task-empty-notes", WHEN, "child")
        self.assertEqual([t["id"] for t in planned["workspace"]["tasks"]], ["task-notes"])
        self.assertEqual(len(planned["trash"]), 2)
        result = plan_subtree_restore(planned["workspace"], planned["trash"], "child")
        self.assertEqual({t["id"] for t in result["workspace"]["tasks"]},
                         {t["id"] for t in self.original["tasks"]})

    def test_partial_group_orphan_collision_project_mismatch_fail_unchanged(self):
        planned = plan_subtree_trash(self.original, [], "task-empty-notes", WHEN, "child")
        invalid = [
            (planned["workspace"], planned["trash"][:1]),
            ({**planned["workspace"], "tasks": []}, planned["trash"]),
            ({**planned["workspace"], "tasks": [
                *planned["workspace"]["tasks"],
                {**self.original["tasks"][2], "parentId":"task-notes"}
            ]}, planned["trash"]),
            (planned["workspace"], [{
                **entry, "task": {**entry["task"], "projectId": None}
            } for entry in planned["trash"]])
        ]
        for workspace, trash in invalid:
            with self.subTest(trash=trash):
                before = deepcopy((workspace, trash))
                with self.assertRaises(BackupError):
                    plan_subtree_restore(workspace, trash, "child")
                self.assertEqual((workspace, trash), before)

    def test_equal_size_group_cannot_contain_unrelated_root_or_mixed_times(self):
        planned = plan_subtree_trash(self.original, [], "task-notes", WHEN, "guard")
        swapped = deepcopy(planned["trash"])
        unrelated = next(entry for entry in swapped if entry["task"]["id"] == "task-grandchild")
        unrelated["task"]["id"] = "unrelated-root"
        unrelated["task"]["parentId"] = None
        with self.assertRaises(BackupError):
            plan_subtree_restore(planned["workspace"], swapped, "guard")
        mixed = deepcopy(planned["trash"])
        mixed[1]["deletedAt"] = "2026-11-03T14:00:00Z"
        with self.assertRaises(BackupError):
            plan_subtree_restore(planned["workspace"], mixed, "guard")
        self.assertEqual(len(plan_subtree_restore(planned["workspace"], planned["trash"], "guard")["workspace"]["tasks"]), 3)

    def test_bad_timestamp_group_capacity_and_stale_id_rejected(self):
        for root, when, group, trash in (
            ("missing", WHEN, "new", []),
            ("task-notes", "invalid", "new", []),
            ("task-notes", WHEN, "", []),
            ("task-notes", WHEN, "duplicate", [{"groupId":"duplicate"}]),
            ("task-notes", WHEN, "new", [{"task":{"id":"task-grandchild"}}]),
            ("task-notes", WHEN, "new", [{"groupId":str(i)} for i in range(1000)])
        ):
            with self.subTest(root=root, when=when, group=group):
                with self.assertRaises(BackupError):
                    plan_subtree_trash(self.original, trash, root, when, group)


if __name__ == "__main__":
    unittest.main()
