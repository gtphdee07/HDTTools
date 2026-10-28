"""ROUND 1 ONLY. Filled ui-redesign-map.json from the measured frames when the inventory had 150 elements.

It overwrites the committed first map and its frames, and it asserts every inventory id is drawn, which is no longer true for the 167-element
inventory. It is kept as the reference for how a full map is derived. It refuses to run without --overwrite-first-round.
"""
import json
import pathlib
import shutil
import sys
from collections import OrderedDict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config  # noqa: E402

INV = config.ANDROID_REDESIGN / 'ui-inventory.json'  # NOTE: the first round ran against the 150-element inventory
DEST = config.RETURN
OUT = config.OUT
import screens_a, screens_b, screens_c  # noqa: E402,F401
from screens_a import STATES  # noqa: E402

TOKEN = {'rgb(22, 19, 31)': 'ink', 'rgb(85, 80, 106)': 'ink-muted', 'rgb(255, 255, 255)': 'surface', 'rgb(8, 115, 121)': 'teal-deep', 'rgb(91, 37, 184)': 'purple-deep',
         'rgb(184, 74, 0)': 'orange-deep', 'rgb(63, 107, 53)': 'pine', 'rgb(154, 58, 46)': 'danger-text', 'rgb(181, 71, 58)': 'danger', 'rgb(87, 103, 117)': 'slate',
         'rgb(18, 181, 174)': 'teal', 'rgb(255, 122, 26)': 'orange', 'rgb(123, 63, 228)': 'purple'}
SCREEN_OF_PREFIX = {'picker': 'rig_picker', 'chooser': 'chooser', 'truck': 'truck_tag_entry', 'trailer': 'trailer_tag_entry', 'scale': 'scale_ticket_entry', 'results': 'results',
                    'history': 'history', 'account': 'account', 'splash': 'splash', 'app_icon': 'app_icon', 'paywall': 'paywall', 'disclaimer': 'disclaimer'}
WRAP_KINDS = {'text', 'notice', 'card', 'panel', 'banner', 'card-button', 'dialog-title', 'text-row'}

NEW_FN = {'truck.reference_focus_badge', 'trailer.reference_focus_badge'}
BACK_FN = "Goes back one screen, the same as the system Back button. Blocked while a paid Scan is in flight."
ADDED = {
    'picker.logo': ('image', 'Logo', 'Brand mark in the top bar.', None, 'Decorative: empty content description. Source web/public/logo.png.'),
    'picker.tagline': ('text', 'Tagline', 'Brand tagline under the app name.', 'Weight safety, before you roll', 'Same words as Web.'),
    'picker.account_status': ('button', 'Account status', 'Shows whether the user is signed in and as whom; opens the account sheet (signed in) or the sign-in route (signed out).', 'Signed in as <email> | Not signed in',
                              'Owner feedback item 3. 48 dp tall. Content description: "Account: signed in as <email>. Opens account menu" or "Not signed in. Sign in".'),
    'picker.account_avatar': ('avatar', 'Account avatar', 'First letter of the email (signed in) or a person icon (signed out).', '<first letter of email>', 'Decorative.'),
    'picker.account_menu': ('bottom-sheet', 'Account menu sheet', 'Bottom sheet with the email, Sign out and Cancel.', None, 'Owner feedback item 4. Opens in one tap from picker.account_status. Cannot be opened while a paid Scan is in flight.'),
    'picker.account_menu_email': ('text', 'Account menu email', 'The signed-in email, repeated in the sheet.', '<email>', None),
    'picker.sign_out_button': ('button', 'Sign out (sheet)', 'Signs the user out, the same action as paywall.sign_out_button.', 'Sign out', 'Destructive style. Existing function, new place.'),
    'picker.account_menu_cancel': ('text-button', 'Cancel (sheet)', 'Closes the account sheet.', 'Cancel', 'Same as tapping outside or the system Back button.'),
    'picker.empty_state': ('panel', 'Empty rigs state', 'Shown when the user has no saved rigs.', 'No saved rigs yet / Finish a check and your rig shows up here. Manual entry is free.', 'New wording (see copy-changes.md).'),
    'chooser.back': ('icon-button', 'Back', BACK_FN, None, 'Content description "Back".'),
    'chooser.loading_text': ('text', 'Scan overlay text', 'Words under the spinner while a Scan is in flight.', 'Reading\u2026', 'Reuses the existing "Reading\u2026" string. The overlay still blocks all taps.'),
    'truck.back': ('icon-button', 'Back', BACK_FN, None, 'Content description "Back".'),
    'truck.reference_focus_badge': ('badge', 'Focused field badge', 'Names the field the pinned reference crop is showing (GVWR, Front GAWR, Rear GAWR).', 'GVWR | Front GAWR | Rear GAWR', 'NEW FUNCTION: needs a stored crop rectangle per field, as fractions of the reference photo. See interaction-notes.md.'),
    'trailer.reference_focus_badge': ('badge', 'Focused field badge', 'Names the field the pinned reference crop is showing (GVWR, GAWR per axle, UVW).', 'GVWR | GAWR per axle | UVW', 'NEW FUNCTION: needs a stored crop rectangle per field. See interaction-notes.md.'),
    'truck.credit_chip': ('chip', 'Scan balance chip', 'Scan balance, top right, as on the Rig picker and Chooser. Opens the Paywall.', '<n> scans | 1 scan | \u2026', 'Added to the Truck screen only because it has a paid stand-alone Scan button. Not on Trailer or Scale.'),
    'trailer.back': ('icon-button', 'Back', BACK_FN, None, 'Content description "Back".'),
    'scale.back': ('icon-button', 'Back', BACK_FN, None, 'Content description "Back".'),
    'results.back': ('icon-button', 'Back', 'Goes back, the same as the system Back button.', None, 'Content description "Back".'),
    'results.verdict_icon': ('icon', 'Verdict icon', 'Check, cross or info glyph in a translucent circle inside the verdict band.', '(CheckCircle | Cancel | Info)', 'Non-colour cue for the verdict. Decorative: the headline carries the meaning.'),
    'results.row_badge': ('badge', 'Row status badge', 'Says the row status in words: Within limit, Over limit or Not checked, with a matching icon.', 'Within limit | Over limit | Not checked', 'Fail never relies on colour alone.'),
    'results.row_chevron': ('icon-button', 'Row note toggle', 'Shows that a row has a note and expands or collapses it.', None, 'Only on rows that have a note (Tow Vehicle Total, Trailer Axle(s), Trailer Total). 48 dp target. Content description "Show note" or "Hide note".'),
    'history.back': ('icon-button', 'Back', 'Goes back, the same as the system Back button.', None, 'Content description "Back".'),
    'account.back': ('icon-button', 'Back', 'Goes back, the same as the "Not now" button.', None, 'Content description "Back".'),
    'splash.background': ('splash', 'Splash background', 'Brand colour behind the splash icon.', None, 'Teal #12b5ae. Android 12+ windowSplashScreenBackground.'),
    'splash.icon': ('splash', 'Splash icon', 'Mark on a sky-gradient disc, shown while the app starts.', None, 'See assets/splash_icon.svg. Owner feedback item 1.'),
    'splash.branding': ('splash', 'Splash branding', 'App name and tagline at the bottom of the splash.', 'RigCheck / Weight safety, before you roll', 'Optional (windowSplashScreenBrandingImage); drop if it cannot be built.'),
}

OV = {
    'picker.app_title': dict(notes='Now in the teal top bar beside the logo and tagline. Outfit 800 26/30.'),
    'picker.history_button': dict(notes='Secondary pill button with a clock icon, 48 dp high. Moved from the top bar to the right of the heading so the top bar holds brand, account and balance.'),
    'picker.credit_chip': dict(new_text='<n> scans | 1 scan | 0 scans (signed out) | \u2026 (only while a signed-in balance loads)',
                               notes='Stays top right. 48 dp high, 26 dp camera icon (was ~28 dp and 16 dp). Content description "Scan balance: N scans. Opens the Paywall". Tap target and navigation unchanged.'),
    'picker.header_divider': dict(status='removed', notes='Removed: the teal top bar with a 24 dp rounded bottom edge separates header from body, so a hairline is not needed.'),
    'picker.rig_card': dict(notes='White card, 1 dp border, shadow-sm, min 84 dp. Chevron added at the right (decorative). Whole card is the tap target. First card carries the ids in the frame; the rest repeat.'),
    'picker.new_rig_label': dict(notes='The new-rig panel is a tinted purple block that scrolls with the list (it was a fixed footer).'),
    'picker.new_rig_input': dict(notes='Standard text field (56 dp). Focus state: 2 dp Teal-deep border plus 4 dp Tint-teal ring.'),
    'picker.create_button': dict(notes='Primary button, 56 dp. Disabled style while the nickname is blank (see rig_picker__in).'),
    'chooser.step_bar': dict(status='replaced', notes='Numbered three-step indicator (Truck, Trailer, Scale) replaces the 8 dp bar. Keeps the visible caption "Step n of 3" so tests can still find it.'),
    'chooser.scan_card': dict(notes='Purple-tinted option card, min 148 dp, 64 dp circular icon. Description text is unchanged; the separator is an em dash as in the app.'),
    'chooser.manual_card': dict(notes='Teal-tinted option card, same size as Scan Photo, so manual entry reads as a first-class path.'),
    'chooser.footer_note': dict(notes='Sunken info row with an info icon.'),
    'chooser.loading_overlay': dict(notes='White wash at 88% with spinner and "Reading\u2026" text. Still blocks every tap during a paid Scan. Back is blocked too.'),
    'chooser.credit_chip': dict(new_text='<n> scans | 1 scan | 0 scans (signed out) | \u2026 (only while a signed-in balance loads)', notes='Same chip and rule as picker.credit_chip.'),
    'photo_dialog.camera': dict(notes='Primary button. Order swapped: Take Photo above Choose from Gallery (today Gallery is first).'),
    'photo_dialog.gallery': dict(notes='Secondary button below Take Photo.'),
    'truck.title': dict(notes='Moved into the top bar (26/30 Outfit 800).'),
    'truck.step_bar': dict(status='replaced', notes='Numbered step indicator in the top bar; collapses away while the keyboard is open.'),
    'truck.reference_image': dict(status='replaced', notes='Pinned reference card above the scrolling form. Shows three lines of the label with the focused field\'s line outlined in orange. No hover or press-and-hold. In the frames the crop is a placeholder; production uses the cropped ref photo (keep the redacted VIN block).'),
    'truck.reference_hint': dict(new_text='Tap a field to see its spot on the tag', notes='Wording changed because a phone has no hover. See copy-changes.md.'),
    'truck.standalone_info': dict(notes='Padded to a 48 dp target (was 24 dp). Content description "What is stand-alone weight?".'),
    'truck.standalone_info_text': dict(notes='Shown on a white strip inside the orange panel after the info icon is tapped.'),
    'truck.standalone_panel': dict(notes='Tint-orange panel, 24 dp radius.'),
    'truck.scan_standalone_button': dict(notes='Secondary button, 52 dp. While a Scan is in flight it reads "Reading\u2026" and is disabled.'),
    'truck.pin_weight_slider': dict(notes='4 dp track, 28 dp thumb, 48 dp touch height (the element is 48 dp tall). Content description "Pin weight, percent of trailer weight". Hidden when the stand-alone field has a value.'),
    'truck.next_button': dict(notes='Primary button, 56 dp, pinned footer with a top shadow. Arrow icon added.'),
    'trailer.title': dict(notes='Moved into the top bar.'),
    'trailer.step_bar': dict(status='replaced', notes='Numbered step indicator in the top bar.'),
    'trailer.reference_image': dict(status='replaced', notes='Pinned reference card, same pattern as the truck screen. Placeholder crop in the frames.'),
    'trailer.reference_hint': dict(new_text='Tap a field to see its spot on the tag', notes='See copy-changes.md.'),
    'trailer.next_button': dict(notes='Primary button, 56 dp, pinned footer.'),
    'scale.title': dict(notes='Moved into the top bar.'),
    'scale.step_bar': dict(status='replaced', notes='Numbered step indicator in the top bar.'),
    'scale.reference_image': dict(notes='Numbered orange badges (1 to 5) are drawn on the ticket image and match the badges on the field labels. Placeholder image in the frames.'),
    'scale.legend': dict(status='replaced', notes='Five numbered pills that wrap, in the same orange badge style as the fields. Text is unchanged ("Scale location", "Steer", "Drive", "Trailer", "Gross"). Replaces orange text on white, which failed contrast.'),
    'scale.location_field': dict(notes='Label carries badge 1. Steer 2, Drive 3, Trailer 4, Gross 5.'),
    'scale.check_button': dict(notes='Primary button, 56 dp, pinned footer.'),
    'disclaimer.icon': dict(notes='72 dp rounded tile in Tint-orange with an Orange-deep warning glyph.'),
    'disclaimer.accept_button': dict(notes='Moved into a pinned footer so the whole page scrolls above it. Fixes the button being pushed off screen at large font sizes. Wording is unchanged.'),
    'disclaimer.body_1': dict(notes='Disclaimer wording is legally reviewed and unchanged.'),
    'disclaimer.body_2': dict(notes='Disclaimer wording is legally reviewed and unchanged.'),
    'results.rig_name': dict(notes='Moved into the top bar next to Back.'),
    'results.date': dict(notes='Moved into the top bar under the rig name.'),
    'results.verdict': dict(notes='Hero band, 24 dp radius, shadow-md. Pass = Pine, Fail = Danger, Partial and Insufficient = Purple. White text. Icon shape differs for each tone.'),
    'results.garage_get_pro': dict(notes='Ghost button, 48 dp.'),
    'results.estimated_notice': dict(notes='Tint-orange notice. The title keeps its warning emoji because the text is frozen; no extra icon is drawn.'),
    'results.breakdown_card': dict(notes='White card, 24 dp radius. Lives inside the page scroll; the card no longer scrolls on its own.'),
    'results.row_icon': dict(notes='26 dp (was 28). Shapes: check-circle, x-circle, info-circle.'),
    'results.row_bar': dict(notes='10 dp rounded bar (was 6 dp). Fill: Pine pass, Danger fail, Slate not checked.'),
    'results.row_note': dict(notes='Sunken note block under the row; shown when the row is expanded.'),
    'results.start_another_button': dict(notes='Primary button, 56 dp, pinned footer.'),
    'history.title': dict(notes='Moved into the top bar.'),
    'history.entry_verdict': dict(notes='Now a pill badge with an icon (Web uses a Badge) instead of coloured text. Words unchanged.'),
    'history.upgrade_button': dict(notes='Ghost button, 48 dp.'),
    'paywall.title': dict(notes='Moved into the top bar.'),
    'paywall.back': dict(status='replaced', notes='The Paywall had no Back control. This is the new back icon button (content description "Back"). Blocked while a purchase is busy.'),
    'paywall.sign_out_button': dict(notes='Ghost button with a logout icon, 48 dp.'),
    'paywall.plan_label': dict(notes='Pill badge.'),
    'paywall.offer_card': dict(notes='Free: one large Tint-purple Pro card. Pro: one white row card per pack. Prices from the store; the frames show a short ($4.99) and a long (CA$12.99 one time) one.'),
    'paywall.buy_button': dict(notes='Primary button. 56 dp on the Pro card, 48 dp inside pack rows. Never shown to a Free account for packs, never to a Pro account for the Pro offer.'),
    'paywall.toast': dict(notes='Snackbar above the Restore button: Ink background, white text.'),
    'paywall.restore_button': dict(notes='Ghost button, 56 dp, pinned footer so the 3-button navigation bar can no longer cover it (ticket #186).'),
    'account.title': dict(notes='Moved into the top bar.'),
    'account.email_field': dict(notes='Same field style as every other screen (it was outlined here and filled elsewhere).'),
    'account.password_field': dict(notes='Same field style. Shows "At least 6 characters" under it when creating an account.'),
    'account.submit_button': dict(notes='Primary button, 56 dp.'),
    'account.google_button': dict(notes='Secondary button. The Google glyph is not drawn; use the official asset when building.'),
    'account.apple_button': dict(notes='Not shown today. Drawn only in account__apple_enabled_future: same style as the Google button.'),
    'account.not_now_button': dict(notes='Ghost button in a pinned footer.'),
    'scan_error.title': dict(notes='M3 AlertDialog restyled: 24 dp radius, 24 dp padding, shadow-md, Outfit 700 22/28 title.'),
    'scan_error.next_step_button': dict(notes='Stacked full-width buttons, 52 dp: first next step is primary, a second is secondary. OK sits last as a ghost button.'),
    'late_scan.title': dict(notes='Same dialog style as the Scan failed dialog.'),
}


def px(v):
    return f'{round(v)}dp'


def main():
    if '--overwrite-first-round' not in sys.argv:
        sys.exit('round1_mapgen.py would overwrite the committed first-round map; pass --overwrite-first-round if you really mean it.')
    inv = json.load(open(INV, encoding='utf-8'))
    order = [f"{s['screen']}__{s['name']}" for s in STATES]
    meta = {n: json.load(open(OUT / 'meta' / f'{n}.json', encoding='utf-8')) for n in order}
    first = {}
    for n in order:
        for e in meta[n]['elements']:
            first.setdefault(e['id'], (n, e))
    # prefer a state of the element's own screen
    own = {}
    for n in order:
        for e in meta[n]['elements']:
            own.setdefault((meta[n]['screen'], e['id']), (n, e))

    def pick(eid, screen):
        return own.get((screen, eid)) or first.get(eid)

    def rank(n, eid):
        return [e['id'] for e in meta[n]['elements']].index(eid) + 1

    ids = {e['id'] for e in inv['elements']}
    missing = [i for i in ids if i not in first and OV.get(i, {}).get('status') != 'removed']
    assert not missing, f'ids never drawn: {missing}'
    for e in inv['elements']:
        r = e['redesign']
        eid = e['id']
        ov = OV.get(eid, {})
        hit = pick(eid, e['screen'])
        if ov.get('status') == 'removed':
            r.update(status='removed', notes=ov['notes'])
            continue
        n, m = hit
        status = ov.get('status') or ('moved' if m['region'] != e['today']['region'] else 'restyled')
        kind = e['kind']
        w = 'fill' if m['w'] >= 330 else ('wrap' if kind in WRAP_KINDS or kind in ('text-button',) else px(m['w']))
        h = f'wrap (~{round(m["h"])}dp)' if kind in WRAP_KINDS else px(m['h'])
        style = m['style']
        if not style:
            col = TOKEN.get(m['color'], m['color'])
            style = f"{m['ff']} {m['fw']} {round(float(m['fs'][:-2]))}/{round(float(m['lh'][:-2])) if m['lh'].endswith('px') else m['lh']} {col}"
            if m['ls'] not in ('normal', '0px'):
                style += f", letter-spacing {m['ls']}"
        note = ov.get('notes', '')
        note = (note + ' ' if note else '') + f'Drawn in {n}.png.'
        r.update(status=status, new_screen=e['screen'], new_region=m['region'], new_order=rank(n, eid), new_width=w, new_height=h, new_style=style,
                 new_text=ov.get('new_text'), new_test_tag=e['test_tag_new'], notes=note)
    added = []
    for aid, (kind, name, fn, text, note) in ADDED.items():
        n, m = first[aid]
        screen = SCREEN_OF_PREFIX[aid.split('.')[0]]
        w = 'fill' if m['w'] >= 380 else px(m['w'])
        h = px(m['h'])
        added.append(OrderedDict([('id', aid), ('screen', screen), ('kind', kind), ('name', name), ('function', fn), ('text', text), ('needs_new_function', aid in NEW_FN),
                                  ('redesign', OrderedDict([('status', 'added'), ('new_screen', screen), ('new_region', m['region']), ('new_order', rank(n, aid)), ('new_width', w), ('new_height', h),
                                                            ('new_style', m['style'] or f"{m['ff']} {m['fw']} {round(float(m['fs'][:-2]))}"), ('new_text', text), ('new_test_tag', aid.replace('.', '_')),
                                                            ('notes', (note + ' ' if note else '') + f'Drawn in {n}.png.')]))]))
    unexpected = set(first) - ids - set(ADDED) - {'app_icon.adaptive', 'app_icon.layers'}
    assert not unexpected, f'unlisted added ids: {unexpected}'
    inv['added_elements'] = added
    inv['meta']['redesign_round'] = {
        'about': 'Filled in by the Claude Design round for ticket #190, 2026-10-27. Sizes and regions are measured from the rendered frames in annotated/ (412 x 892 dp).',
        'decisions': {'dark_theme': 'No, light only', 'navigation': 'Re-skin plus layout rework, same flow and same 9 routes; a top app bar was added', 'timing': 'Design started from the inventory and the live Web app; baseline frames (#189) were not available, so sizes are estimates of today\'s app'},
        'status_note': 'redesign.status holds the first word of status_values (kept, restyled, moved, merged, split, removed, replaced). Added elements carry "added".',
        'frames': len(order),
    }
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / 'annotated').mkdir(exist_ok=True)
    for n in order:
        shutil.copy(OUT / 'png' / f'{n}.png', DEST / 'annotated' / f'{n}.png')
    (DEST / 'ui-redesign-map.json').write_text(json.dumps(inv, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    known = ids | set(ADDED)
    legends = {n: [{'n': e['n'], 'id': e['id']} for e in meta[n]['elements'] if e['id'] in known] for n in order}
    (DEST / 'annotation-legends.json').write_text(json.dumps(legends, indent=1) + '\n', encoding='utf-8')
    counts = {}
    for e in inv['elements']:
        counts[e['redesign']['status']] = counts.get(e['redesign']['status'], 0) + 1
    print(counts, 'added', len(added), 'frames', len(order))


if __name__ == '__main__':
    main()
