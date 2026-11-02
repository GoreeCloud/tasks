"""Isolated schema-4 recovery-group reference; never invoked by live task APIs."""
from copy import deepcopy
import re
from backup import _timestamp, BackupError


def verify_manifest(m, trash):
    if (type(m) is not dict or type(m.get('groupId')) is not str or
            not re.fullmatch(r'[A-Za-z0-9-]{1,128}', m['groupId']) or
            type(m.get('groupRootId')) is not str or not m['groupRootId'] or
            not _timestamp(m.get('deletedAt'))):
        raise BackupError('Invalid independent manifest')
    members = m.get('memberIds')
    if (type(members) is not list or not 1 <= len(members) <= 1000 or
            any(type(x) is not str or not x or len(x) > 128 for x in members) or
            members != sorted(set(members)) or m['groupRootId'] not in members or
            type(trash) is not list):
        raise BackupError('Invalid manifest members')
    rows = [e for e in trash if type(e) is dict and e.get('groupId') == m['groupId']]
    if len(rows) != len(members) or sorted(e.get('task',{}).get('id') for e in rows) != members:
        raise BackupError('Group member mismatch')
    if any(e.get('groupRootId') != m['groupRootId'] or
           e.get('deletedAt') != m['deletedAt'] or
           e.get('groupSize') != len(members) for e in rows):
        raise BackupError('Group metadata mismatch')
    return True


def create_manifest(trash, group_id):
    rows = [e for e in trash if type(e) is dict and e.get('groupId') == group_id]
    if not rows:
        raise BackupError('Missing group')
    m = {'groupId': group_id, 'groupRootId': rows[0]['groupRootId'],
         'deletedAt': rows[0]['deletedAt'],
         'memberIds': sorted(e['task']['id'] for e in rows)}
    verify_manifest(m, trash)
    return deepcopy(m)
