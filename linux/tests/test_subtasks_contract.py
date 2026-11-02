"""Proposed schema 4 is validated offline, never restored by legacy import."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import BackupError, validate as production_validate
from subtasks_contract import parse_proposed_graph, validate_proposed_graph


FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures/portable/schema4-proposed-synthetic.json'


class ProposedSubtasksTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.data = json.loads(self.raw)

    def fail_mutation(self, mutation):
        snapshot = deepcopy(self.data)
        mutation(snapshot)
        with self.assertRaises(BackupError):
            validate_proposed_graph(snapshot)

    def test_valid_proposed_graph_remains_unimportable(self):
        graph = parse_proposed_graph(self.raw)
        self.assertEqual(graph['depths'], {
            'task-notes': 1, 'task-empty-notes': 2, 'task-grandchild': 3
        })
        self.assertEqual(graph['tasks'][0]['completedAt'], self.data['tasks'][0]['completedAt'])
        self.assertEqual(graph['tasks'][0]['labels'], ['Work', 'Design 🧭'])
        with self.assertRaises(BackupError):
            production_validate(self.data)

    def test_refuses_cycle_orphan_and_cross_project(self):
        for mutation in (
            lambda d: d['tasks'][1].update(parentId='orphan'),
            lambda d: d['tasks'][0].update(parentId='task-grandchild'),
            lambda d: d['tasks'][1].update(parentId=d['tasks'][1]['id']),
            lambda d: d['tasks'][1].update(projectId=None),
            lambda d: d['tasks'][1].pop('parentId'),
            lambda d: d['tasks'][1].update(parentId=23),
            lambda d: d['tasks'][0].update(labels=['Work', 'Work']),
            lambda d: d['tasks'].append(dict(d['tasks'][1])),
        ):
            with self.subTest(mutation=mutation):
                self.fail_mutation(mutation)

    def test_limits(self):
        self.fail_mutation(lambda d: d['tasks'].append({
            **d['tasks'][2], 'id':'fourth', 'parentId':'task-grandchild'
        }))
        def many(d):
            for n in range(299):
                d['tasks'].append({**d['tasks'][1], 'id':f'extra-{n}', 'parentId':'task-notes'})
        self.fail_mutation(many)

    def test_does_not_mutate_inputs(self):
        snapshot = deepcopy(self.data)
        validate_proposed_graph(snapshot)
        self.assertEqual(snapshot,self.data)
        with self.assertRaises(BackupError):
            parse_proposed_graph(b' ' * (2*1024*1024+1))


if __name__ == '__main__':
    unittest.main()
