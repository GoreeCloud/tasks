"""Legacy backup conversion is only a pure preflight, never a restore or migration."""
import json
from pathlib import Path
from copy import deepcopy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import validate, BackupError
from subtasks_contract import validate_proposed_graph
from subtasks_migration_preview import preview_legacy_as_roots

ROOT=Path(__file__).resolve().parents[2] / 'fixtures/portable'

class LegacyRootPreviewTests(unittest.TestCase):
    def test_all_three_legacy_schema_versions_have_lossless_root_preview(self):
        for name in ('schema1-synthetic.json','schema2-synthetic.json','schema3-synthetic.json'):
            with self.subTest(name=name):
                source=json.loads((ROOT/name).read_text(encoding='utf-8'))
                original=deepcopy(source)
                current=validate(source)
                projected=preview_legacy_as_roots(source)
                self.assertEqual(source,original)
                self.assertEqual(projected['schema'],4)
                self.assertEqual(projected['projects'],current['projects'])
                self.assertEqual(len(projected['tasks']),len(current['tasks']))
                for next_task,previous in zip(projected['tasks'],current['tasks']):
                    self.assertIsNone(next_task['parentId'])
                    self.assertEqual(next_task['description'],previous.get('description',''))
                    self.assertEqual(next_task['labels'],previous.get('labels',[]))
                    self.assertEqual({k:v for k,v in next_task.items()
                                      if k not in ('parentId','description','labels')},
                                     {k:v for k,v in previous.items()
                                      if k not in ('description','labels')})
                self.assertTrue(all(d==1 for d in validate_proposed_graph(projected)['depths'].values()))

    def test_v4_input_and_over_capacity_projects_cannot_be_flattened(self):
        with self.assertRaises(BackupError):
            preview_legacy_as_roots(json.loads((ROOT/'schema4-proposed-synthetic.json').read_text()))
        sample=json.loads((ROOT/'schema3-synthetic.json').read_text())
        sample['tasks']=[{**sample['tasks'][0],'id':f'item-{i}'} for i in range(301)]
        with self.assertRaises(BackupError):
            preview_legacy_as_roots(sample)
