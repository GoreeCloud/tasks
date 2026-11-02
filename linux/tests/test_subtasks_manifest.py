"""Isolated recovery manifest failure-mode tests: no personal data or disk DB."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backup import BackupError
from subtasks_recovery import plan_subtree_trash
from subtasks_manifest import create_manifest, verify_manifest

class ManifestContractTests(unittest.TestCase):
    def setUp(self):
        f=Path(__file__).resolve().parents[2]/'fixtures/portable/schema4-proposed-synthetic.json'
        workspace=json.loads(f.read_text(encoding='utf-8'))
        self.plan=plan_subtree_trash(workspace,[],'task-notes','2026-11-02T14:00:00Z','g-1')
        self.trash=self.plan['trash']
        self.manifest=create_manifest(self.trash,'g-1')

    def test_manifest_does_not_change_data(self):
        self.assertTrue(verify_manifest(self.manifest,self.trash))
        self.assertEqual(self.manifest['memberIds'],['task-empty-notes','task-grandchild','task-notes'])

    def test_deleted_leaf_hidden_by_forged_counts_is_detected(self):
        changed=[dict(e) for e in self.trash if e['task']['id']!='task-grandchild']
        for row in changed: row['groupSize']=len(changed)
        with self.assertRaises(BackupError):
            verify_manifest(self.manifest,changed)
        self.assertTrue(verify_manifest(self.manifest,self.trash))

    def test_manifests_cannot_change_member_set_or_group_metadata(self):
        for changed in (dict(self.manifest,memberIds=['task-empty-notes','task-notes']),
                        dict(self.manifest,memberIds=list(reversed(self.manifest['memberIds']))),
                        dict(self.manifest,groupRootId='unrelated')):
            with self.assertRaises(BackupError):
                verify_manifest(changed,self.trash)

if __name__=='__main__': unittest.main()
