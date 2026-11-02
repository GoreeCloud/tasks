"""Isolated schema-4 recovery-group reference; never invoked by live task APIs."""
from copy import deepcopy
import hashlib
import json
import re
from backup import _timestamp, BackupError


def payload_digest(task):
    data = json.dumps(task, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


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
            type(trash) is not list or
            type(m.get('memberDigests')) is not list or
            len(m['memberDigests']) != len(members) or
            any(type(h) is not str or len(h) != 64 or
                any(c not in '0123456789abcdef' for c in h) for h in m['memberDigests'])):
        raise BackupError('Invalid manifest members')
    rows = [e for e in trash if type(e) is dict and e.get('groupId') == m['groupId']]
    if len(rows) != len(members) or sorted(e.get('task',{}).get('id') for e in rows) != members:
        raise BackupError('Group member mismatch')
    if any(e.get('groupRootId') != m['groupRootId'] or
           e.get('deletedAt') != m['deletedAt'] or
           e.get('groupSize') != len(members) for e in rows):
        raise BackupError('Group metadata mismatch')
    tasks = {e['task']['id']: e['task'] for e in rows}
    if [payload_digest(tasks[i]) for i in members] != m['memberDigests']:
        raise BackupError('Group payload digest mismatch')
    return True


def create_manifest(trash, group_id):
    rows = [e for e in trash if type(e) is dict and e.get('groupId') == group_id]
    if not rows:
        raise BackupError('Missing group')
    m = {'groupId': group_id, 'groupRootId': rows[0]['groupRootId'],
         'deletedAt': rows[0]['deletedAt'],
         'memberIds': sorted(e['task']['id'] for e in rows)}
    by_id = {e['task']['id']: e['task'] for e in rows}
    m['memberDigests'] = [payload_digest(by_id[i]) for i in m['memberIds']]
    verify_manifest(m, trash)
    return deepcopy(m)
