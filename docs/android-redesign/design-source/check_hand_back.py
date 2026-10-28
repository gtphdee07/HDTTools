import json
import pathlib
import re
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config  # noqa: E402

R = config.ANDROID_REDESIGN
D = config.RETURN
inv = json.load(open(R / 'ui-inventory.json', encoding='utf-8'))
m1 = json.load(open(D / 'ui-redesign-map.json', encoding='utf-8'))
m2 = json.load(open(D / 'ui-redesign-map-followup.json', encoding='utf-8'))
by = {e['id']: e for e in inv['elements']}
ids2 = [e['id'] for e in m2['elements']]
assert len(ids2) == 17 and len(set(ids2)) == 17
ids1 = {e['id'] for e in m1['elements']}
assert ids1 | set(ids2) == set(by) and not ids1 & set(ids2), 'the two maps must cover all 167 ids exactly once'
ok = {'kept', 'restyled', 'moved', 'merged', 'split', 'removed', 'replaced'}
need = ['status', 'new_screen', 'new_region', 'new_order', 'new_width', 'new_height', 'new_style', 'new_test_tag', 'notes']
for e in m2['elements']:
    r = e['redesign']
    assert r['status'] in ok, e['id']
    assert all(r[k] not in (None, '') for k in need), (e['id'], [k for k in need if r[k] in (None, '')])
    assert r['new_test_tag'] == by[e['id']]['test_tag_new'], e['id']
    assert r['new_screen'] == by[e['id']]['screen'], e['id']
    for k in by[e['id']]:
        if k != 'redesign':
            assert e[k] == by[e['id']][k], (e['id'], k)
# the added list is empty and the revised entry names a tag
assert m2['added_elements'] == []
assert m2['revised_elements'][0]['redesign']['new_test_tag'] == 'paywall_toast'
# every frame in the brief exists, at 824 x 1784
brief = ['rig_picker__in', 'rig_picker__new_rig_typing', 'rig_picker__account_menu', 'account__sign_in', 'account__create_account', 'paywall__free_pro_offer', 'paywall__pro_packs',
         'delete_rig_dialog__question', 'delete_rig_dialog__deleting', 'delete_rig_dialog__delete_failed', 'crash_report_dialog__question', 'crash_report_dialog__no_email_app',
         'rig_picker__feedback_no_mail', 'account__feedback_no_mail']


def size(p):
    b = p.read_bytes()
    assert b[:8] == b'\x89PNG\r\n\x1a\n'
    return struct.unpack('>II', b[16:24])


pngs = {p.stem: p for p in (D / 'annotated').glob('*.png')}
for n in brief:
    assert n in pngs, n
    assert size(pngs[n]) == (824, 1784), (n, size(pngs[n]))
bad = [n for n, p in pngs.items() if n != 'app_icon__launcher' and size(p) != (824, 1784)]
assert not bad, bad
# legends: one per frame, ids known, each of the 17 ids is tagged in a frame its notes name
leg = json.load(open(D / 'annotation-legends.json', encoding='utf-8'))
assert set(leg) == set(pngs), set(leg) ^ set(pngs)
known = set(by) | {a['id'] for a in m1['added_elements']}
for n, items in leg.items():
    assert all(i['id'] in known for i in items), n
    assert [i['n'] for i in items] == sorted(i['n'] for i in items)
for e in m2['elements']:
    frame = re.search(r'Drawn in (\S+)\.png', e['redesign']['notes']).group(1)
    assert frame in leg and any(i['id'] == e['id'] for i in leg[frame]), (e['id'], frame)
# every listed new and reissued frame exists
for n in m2['frames']['new'] + m2['frames']['reissued']:
    assert n in pngs, n
print('ok: 17 ids, 167 covered, %d frames, %d new, %d re-issued' % (len(pngs), len(m2['frames']['new']), len(m2['frames']['reissued'])))
