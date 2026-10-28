"""ROUND 2 (the follow-up for the 17 controls). A worked example of a DELTA round: it compares the freshly built frames with the committed ones,
copies only the new and changed PNGs, fills the map entries for a fixed list of ids (NEW17) and rebuilds the legends.

It cannot be re-run on the committed state: once the frames are copied, nothing is new or changed, so it would write empty frame lists.
It refuses to run if ui-redesign-map-followup.json exists unless --overwrite. Copy it and change NEW17 and NOTES for a new delta round.
"""
import hashlib
import json
import pathlib
import shutil
import sys
from collections import OrderedDict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config  # noqa: E402

R = config.ANDROID_REDESIGN
DEST = config.RETURN
OUT = config.OUT
import screens_a, screens_b, screens_c  # noqa: E402,F401
from screens_a import STATES  # noqa: E402

TOKEN = {'rgb(22, 19, 31)': 'ink', 'rgb(85, 80, 106)': 'ink-muted', 'rgb(255, 255, 255)': 'surface', 'rgb(8, 115, 121)': 'teal-deep', 'rgb(91, 37, 184)': 'purple-deep',
         'rgb(184, 74, 0)': 'orange-deep', 'rgb(63, 107, 53)': 'pine', 'rgb(154, 58, 46)': 'danger-text', 'rgb(181, 71, 58)': 'danger', 'rgb(87, 103, 117)': 'slate'}
WRAP_KINDS = {'text', 'notice', 'card', 'panel', 'banner', 'card-button', 'dialog-title', 'text-row', 'dialog'}

NEW17 = ['picker.rig_delete_button', 'picker.feedback_link', 'picker.feedback_no_mail', 'account.feedback_link', 'account.feedback_no_mail', 'paywall.beta_label',
         'delete_rig.dialog', 'delete_rig.title', 'delete_rig.body', 'delete_rig.error', 'delete_rig.confirm_button', 'delete_rig.cancel_button',
         'crash_prompt.question', 'crash_prompt.details', 'crash_prompt.no_mail_app', 'crash_prompt.send_button', 'crash_prompt.dismiss_button']

NOTES = {
    'picker.rig_delete_button': 'Answer to question 1. A 48 x 48 dp icon button at the right end of every Rig card: a 24 dp trash icon in ink-muted, after a 1 dp vertical divider (40 dp tall) and with a 4 dp right margin. The divider splits the card in two: the left part (avatar, text, chevron) is the only part that starts a check, the right part is the bin and nothing else. Their ripples and hit areas never overlap, so a tap on the bin cannot start a check. Content description "Delete <nickname>". Shown only when signed in. One per card; the frame tags the first card, the others repeat. Pressed: ripple confined to the bin, icon turns danger-text.',
    'picker.feedback_link': 'Ghost button (teal-deep text, 48 dp high) centred at the end of the scrolling body, below the new-rig panel. It was orange text in the footer; orange text fails contrast on white, and the screen has no pinned footer, so it moved into the body. Opens the email app.',
    'picker.feedback_no_mail': 'Caption (13/18, ink-muted, centred) directly under the link. The address in the frame, WTIAppDev@gmail.com, is the beta address from docs/BETA_PLAN.md; the app fills in its own constant.',
    'account.feedback_link': 'Ghost button, 48 dp, centred below "Continue with Google" (and "Continue with Apple" when enabled), above the pinned "Not now". Same component as picker.feedback_link. Not hidden while an account request is busy, so a user stuck on sign-in can still write.',
    'account.feedback_no_mail': 'Caption under the link, same style as picker.feedback_no_mail.',
    'paywall.beta_label': 'Notice card, tone "scan" (tint-orange fill, orange-deep info icon), bold body-sm text, full width at the very top of the body, above the "Buying for" line. BETA BUILD ONLY: every Paywall frame in this round is drawn as a beta build shows it. A production build leaves the notice out and everything below moves up by 68 dp.',
    'delete_rig.dialog': 'Answer: keeps the Material 3 AlertDialog shape, restyled like the Scan failed dialog (24 dp radius, 24 dp padding, 364 dp wide, shadow md, scrim at 55%). Opens over the Rig picker. Dismiss by scrim tap or Back is the same as Cancel, and is ignored while the delete runs.',
    'delete_rig.title': 'Title style title-lg (Outfit 700 22/28). The nickname is quoted.',
    'delete_rig.body': 'Body 16/24 ink.',
    'delete_rig.error': 'Only after a failed delete (frame delete_rig_dialog__delete_failed). body-sm 500 in danger-text, under the body text, above the buttons. The dialog stays open so the user can try again.',
    'delete_rig.confirm_button': 'Destructive button, 52 dp, full width, first of the stacked buttons. While the delete runs it reads "Deleting\u2026" and is drawn disabled (frame delete_rig_dialog__deleting).',
    'delete_rig.cancel_button': 'Ghost button, 52 dp, below the confirm button. Disabled while the delete runs.',
    'crash_prompt.question': 'Drawn as the dialog heading (title-lg) because there is no separate title; today it is the AlertDialog body. Opens over whatever screen the app starts on (the frame uses the Rig picker). Replaced by crash_prompt.no_mail_app when Send finds no mail app.',
    'crash_prompt.details': 'body-sm in ink-muted under the question. Hidden together with the question after "no email app".',
    'crash_prompt.no_mail_app': 'Replaces the question and details (frame crash_report_dialog__no_email_app). Body 16/24 in ink. The address in the frame is the beta address; the app fills in its own constant.',
    'crash_prompt.send_button': 'Primary button, 52 dp, full width, first of the stacked buttons. Hidden once the no-mail line replaces the question.',
    'crash_prompt.dismiss_button': 'Ghost button, 52 dp. Reads "Not now" with the question and "OK" after the no-mail line. It is the only button after the no-mail line.',
}


def px(v):
    return f'{round(v)}dp'


def main():
    if (DEST / 'ui-redesign-map-followup.json').exists() and '--overwrite' not in sys.argv:
        sys.exit('ui-redesign-map-followup.json already exists; copy this script for a new delta round, or pass --overwrite.')
    inv = json.load(open(R / 'ui-inventory.json', encoding='utf-8'))
    first_map = json.load(open(DEST / 'ui-redesign-map.json', encoding='utf-8'))
    by_id = {e['id']: e for e in inv['elements']}
    assert len(inv['elements']) == 167
    first_ids = {e['id'] for e in first_map['elements']}
    assert set(by_id) - first_ids == set(NEW17), 'the 17 new ids differ from the brief'
    order = [f"{s['screen']}__{s['name']}" for s in STATES]
    meta = {n: json.load(open(OUT / 'meta' / f'{n}.json', encoding='utf-8')) for n in order}

    # canonical frame per new id: first frame (in STATES order) of the element's own screen, else first anywhere
    own, anyf = {}, {}
    for n in order:
        for e in meta[n]['elements']:
            anyf.setdefault(e['id'], (n, e))
            own.setdefault((meta[n]['screen'], e['id']), (n, e))
    out_elements = []
    for eid in NEW17:
        e = json.loads(json.dumps(by_id[eid]))
        hit = own.get((e['screen'], eid)) or anyf.get(eid)
        assert hit, f'{eid} is not drawn in any frame'
        n, m = hit
        kind = e['kind']
        status = 'moved' if m['region'] != e['today']['region'] else 'restyled'
        w = 'fill' if m['w'] >= 330 else ('wrap' if kind in WRAP_KINDS or kind == 'text-button' else px(m['w']))
        h = f'wrap (~{round(m["h"])}dp)' if kind in WRAP_KINDS else px(m['h'])
        style = m['style']
        if not style:
            col = TOKEN.get(m['color'], m['color'])
            lh = round(float(m['lh'][:-2])) if m['lh'].endswith('px') else m['lh']
            style = f"{m['ff']} {m['fw']} {round(float(m['fs'][:-2]))}/{lh} {col}"
        rank = [x['id'] for x in meta[n]['elements']].index(eid) + 1
        e['redesign'] = OrderedDict([('status', status), ('new_screen', e['screen']), ('new_region', m['region']), ('new_order', rank), ('new_width', w), ('new_height', h),
                                     ('new_style', style), ('new_text', None), ('new_test_tag', e['test_tag_new']), ('notes', NOTES[eid] + f' Drawn in {n}.png.')])
        out_elements.append(e)

    # revised first-round entries
    n, m = anyf['paywall.toast']
    revised = [OrderedDict([
        ('id', 'paywall.toast'),
        ('replaces_first_round_entry', True),
        ('redesign', OrderedDict([('status', 'replaced'), ('new_screen', 'paywall'), ('new_region', m['region']), ('new_order', [x['id'] for x in meta[n]['elements']].index('paywall.toast') + 1),
                                  ('new_width', 'fill'), ('new_height', px(m['h'])), ('new_style', 'Snackbar'), ('new_text', None), ('new_test_tag', 'paywall_toast'),
                                  ('notes', 'Answer to question 2: replace the system Toast with a Material 3 Snackbar (same id, so no new id is needed). The frames already drew it: ink fill, white body-md text, 14 dp radius, 16 dp side margins, shadow md, sitting 148 dp above the bottom edge (above the pinned Restore button). Shown 4 s, then it fades. No action button. Needs a test tag: the updated inventory has none for paywall.toast (a system Toast cannot be tagged), so use "paywall_toast". Messages are unchanged ("Purchase complete!", "Pro unlocked!", "Purchases restored.", the store error). Code change: SnackbarHost in the Paywall re-skin ticket. Drawn in ' + n + '.png.')]))]),
    ]
    drift = [
        'paywall.back: the updated inventory (after #186) says it is an M3 TextButton with a 24 dp ArrowBack icon and the label "Back", not "missing". The first round drew an icon-only 48 dp back button for it (content description "Back"). If tests find it by the visible word "Back", the re-skin must keep that text or move those tests to the tag paywall_back. Nothing in the frames changes.',
        'Every other first-round element: only tests_referencing changed in the updated inventory (the counts moved from text lookups to tag lookups).',
    ]

    # frames: copy new and changed
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    reissued, new = [], []
    (DEST / 'annotated').mkdir(exist_ok=True)
    for p in sorted((OUT / 'png').glob('*.png')):
        o = DEST / 'annotated' / p.name
        if not o.exists():
            new.append(p.stem)
        elif h(o) != h(p):
            reissued.append(p.stem)
        else:
            continue
        shutil.copy(p, o)
    print('new', new)
    print('reissued', reissued)

    result = OrderedDict([
        ('about', 'Follow-up design round for the 17 controls the first hand-back did not cover (DESIGN_FOLLOWUP_BRIEF.md). Same format as ui-redesign-map.json: each entry is the updated inventory record with `redesign` filled. Sizes, regions and order are measured from the rendered frames.'),
        ('inventory_elements', 167),
        ('status_note', 'redesign.status is the first word of meta.status_values, as in the first map. `moved` here means the region changed against the inventory\'s `today`.'),
        ('elements', out_elements),
        ('added_elements', []),
        ('revised_elements', revised),
        ('answers', OrderedDict([
            ('bin_on_rig_card', 'A 48 dp trash icon button at the right end of the card, behind a 1 dp vertical divider. The card body to the left of the divider is the only part that starts a check; the bin has its own hit area and ripple. See picker.rig_delete_button.'),
            ('paywall_toast', 'Replace the system Toast with a Snackbar; keep the id paywall.toast and give it the test tag paywall_toast. See revised_elements.'),
        ])),
        ('frames', OrderedDict([('new', new), ('reissued', reissued), ('beta_build_only', [f for f in reissued + new if f.startswith('paywall__')])])),
        ('drift_notes', drift),
        ('needs_new_function', 'None. Everything drawn already exists in the app (#169, #172, #184).'),
    ])
    (DEST / 'ui-redesign-map-followup.json').write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

    # legends for every frame, ids limited to ones the maps know
    known = set(by_id) | {a['id'] for a in first_map['added_elements']}
    legends = {n: [{'n': e['n'], 'id': e['id']} for e in meta[n]['elements'] if e['id'] in known] for n in order}
    old = json.load(open(DEST / 'annotation-legends.json', encoding='utf-8'))
    changed_legends = [n for n in old if n in legends and old[n] != legends[n]]
    print('legends changed for', changed_legends)
    assert set(changed_legends) <= set(reissued), 'a legend changed for a frame that was not re-issued'
    (DEST / 'annotation-legends.json').write_text(json.dumps(legends, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
