"""Disclaimer, Results, History, Paywall, Account, dialogs, splash and app icon."""
from lib import *
from screens_a import add, picker, chooser, EMAIL

PIN_NOTE = "Steer + drive axle readings vs. your truck tag's GVWR."


def with_overlay(base_html, overlay_inner):
    return base_html[:-6] + f'<div data-region="overlay" style="position:absolute;left:0;top:0;width:412px;height:892px">{overlay_inner}</div></div>'


# ======================= Disclaimer =======================
def disclaimer(scale=1.0):
    s = lambda n: round(n * scale)
    body = (div(icon('warning', 40, ORANGE_DEEP), _id='disclaimer.icon', _sn='IconTile', display='flex', align_items='center', justify_content='center', width=72, height=72, border_radius=24, background=TINT_ORANGE)
            + h_out('Experimental Tool —<br>Not for Safety Decisions', s(28), s(34), 800, _id='disclaimer.title', letter_spacing='-0.01em')
            + text('RigCheck is an experimental project built to learn app development, not a certified or professional weight-safety tool. You type in numbers straight off your own tag and ticket photos, and the math that follows is simplified — any step of that chain can be wrong.', s(16), s(24), 400, INK, _id='disclaimer.body_1')
            + text("Do not use this tool to decide whether your rig is safe to tow. Always verify actual weights and ratings using a certified scale and your vehicle's official documentation, and consult a qualified professional if you're unsure. You use this tool, and any decisions you make based on it, entirely at your own risk and responsibility.", s(16), s(24), 400, INK, _id='disclaimer.body_2'))
    ftr = btn('primary', 'I Understand, Continue', 'disclaimer.accept_button')
    return lambda sc: phone('<div data-region="header" style="height:36px;flex-shrink:0;background:#fff7ee"></div>', body, ftr, scroll=sc, bg=WHITE, body_pad='28px 20px 0', body_gap=18, fade=True)


add('disclaimer', 'default', disclaimer())
add('disclaimer', 'large_font', disclaimer(1.6))

# ======================= Results =======================
ROWS = ['Front Axle (Steer)', 'Rear Axle (Drive)', 'Tow Vehicle Total (GVWR)', 'Trailer Axle(s)', 'Trailer Total (GVWR)', 'Combined Rig Weight']
LIMITS = [6000, 9900, 14000, 14000, 11990, 26000]
NOTES = [None, None, PIN_NOTE, "Trailer axle rating: 2 axle(s) at the tag's per-axle rating.",
         'Includes an estimated 1,480 lb pin weight (steer + drive minus your truck\'s stand-alone weight).', None]
SAFE = [4900, 7600, 12500, 9600, 11100, 22100]
UNSAFE = [5200, 9100, 14300, 9600, 11100, 23400]


def result_row(i, actual, tone, ids=False, expanded=False, last=False):
    label, limit, note = ROWS[i], LIMITS[i], NOTES[i]
    pct = 0 if tone == 'insufficient' else round(actual / limit * 100)
    ic, icc = {'pass': ('check_circle', PINE), 'fail': ('x_circle', DANGER_TEXT), 'insufficient': ('info_circle', SLATE)}[tone]
    bd = {'pass': ('Within limit', 'pass', 'check_circle'), 'fail': ('Over limit', 'fail', 'x_circle'), 'insufficient': ('Not checked', 'notchecked', 'info_circle')}[tone]
    bar_c = {'pass': PINE, 'fail': DANGER, 'insufficient': SLATE}[tone]
    I = (lambda n: n) if ids else (lambda n: None)
    top = row(div(icon(ic, 26, icc, 2.2), _id=I('results.row_icon'), _sn='StatusIcon') + h_out(label, 17, 22, 700, _id=I('results.row_label'), flex_grow=1)
              + badge(bd[0], bd[1], I('results.row_badge'), bd[2])
              + (div(icon('chevron_up' if expanded else 'chevron_down', 24, MUTED), _id='results.row_chevron' if i == 2 else None, _sn='Chevron/48', flex_shrink=0, display='flex', align_items='center', justify_content='center', width=48, height=48, margin='-10px -12px -10px -4px') if note else ''), gap=10)
    bar = div(div('', height=10, border_radius=999, width=f'{min(100, pct)}%', background=bar_c), _id=I('results.row_bar'), _sn='ProgressBar', height=10, border_radius=999, background='#e7edf0', overflow='hidden')
    vals = row(text(f'{0 if tone == "insufficient" else actual:,} lb of {limit:,} lb', 14, 18, 400, MUTED, _id=I('results.row_values'))
               + text(f'{pct}%', 14, 18, 700, DANGER_TEXT if tone == 'fail' else INK, _id=I('results.row_pct')), gap=8, justify_content='space-between', align='baseline')
    nt = text(note, 14, 20, 400, INK, _id='results.row_note', background=SUNKEN, border_radius=14, padding='10px 12px') if (expanded and note) else ''
    return div(top + bar + vals + nt, _id=I('results.row'), _sn='BreakdownRow', display='flex', flex_direction='column', gap=8, padding='14px 0', border_bottom='none' if last else f'1px solid {BORDER}')


def verdict_hero(tone, headline, sub):
    bg = {'pass': PINE, 'fail': DANGER, 'insufficient': PURPLE}[tone]
    ic = {'pass': 'check_circle', 'fail': 'x_circle', 'insufficient': 'info_circle'}[tone]
    return div(div(icon(ic, 36, WHITE, 2.4), _id='results.verdict_icon', _sn='VerdictIcon', display='flex', align_items='center', justify_content='center', width=64, height=64, border_radius=999, background='rgba(255,255,255,0.22)', flex_shrink=0)
               + col(h_out(headline, 30, 34, 800, WHITE, letter_spacing='-0.01em') + text(sub, 15, 21, 400, WHITE), gap=4),
               _id='results.verdict', _sn='VerdictBand', _tag='tr', display='flex', align_items='center', gap=16, background=bg, color=WHITE, border_radius=24, padding=20, box_shadow=SH_MD)


EST_BULLETS = ["Trim, engine, axle ratio, cab/bed size, and factory options change a specific vehicle's real payload — a GVWR/GAWR from a compliance label is a rating, not a guarantee for every configuration.",
               "This estimate doesn't account for passengers, cargo in the cab or bed, or aftermarket accessories — all of which reduce what's actually left for towing.",
               "Before buying, confirm the actual ratings on that specific vehicle's own certification label, and the trailer's own data plate — not an average, a brochure figure, or this estimate.",
               'Actual results may differ. You are solely responsible for safe towing and for complying with all applicable federal and state regulations, including FMCSA and DOT requirements.']


def results(kind='safe', notices=False, expanded=None):
    if kind == 'safe':
        tones = ['pass'] * 6
        actual = SAFE
        hero = verdict_hero('pass', 'Safe to Tow', 'Every axle checks out under its rated limit.')
        idx = list(range(6))
    elif kind == 'unsafe':
        actual = UNSAFE
        tones = ['pass', 'pass', 'fail', 'pass', 'pass', 'pass']
        hero = verdict_hero('fail', 'Not Safe to Tow', 'One or more axles are over their rated limit — see the breakdown below.')
        idx = list(range(6))
    elif kind == 'partial':
        actual = [4900, 7600, 12500, 0, 0, 0]
        tones = ['pass', 'pass', 'pass', 'insufficient', 'insufficient', 'insufficient']
        hero = verdict_hero('insufficient', 'Partially Checked', "Some axles couldn't be checked yet — add more data for a complete picture.")
        idx = list(range(5))
    else:
        actual = [0] * 6
        tones = ['insufficient'] * 6
        hero = verdict_hero('insufficient', 'Not Enough Information', 'Add at least a truck tag, trailer tag, or scale ticket to check anything.')
        idx = list(range(5))
    if kind == 'safe' and expanded is None:
        pass
    exp_i = 2 if kind == 'unsafe' else expanded
    rows_html = ''.join(result_row(i, actual[i], tones[i], ids=(k == 0), expanded=(i == exp_i), last=(k == len(idx) - 1)) for k, i in enumerate(idx))
    hdr = header('Summer rig', back='results.back', sub='Oct 27, 2026', title_id='results.rig_name', sub_id='results.date', pad_bottom=16)
    parts = [hero]
    if notices:
        parts.append(None)
        parts[-1] = notice(''.join(f'<div style="margin-top:6px">•&nbsp;&nbsp;{b}</div>' for b in EST_BULLETS), 'warn', 'results.estimated_notice', title='⚠️ Estimated Figures — Confirm Before You Buy', icn='')
        parts.append(col(notice('Your Garage is full (3 of 3), so "Lakeside" wasn\'t saved to it. Your check is not affected.', 'info', 'results.garage_notice')
                         + btn('ghost', 'Get Pro for a bigger Garage', 'results.garage_get_pro', h=48, full=False, size=15), gap=2))
        parts.append(notice("We couldn't save this check to your History. Your check is not affected.", 'info', 'results.history_notice'))
    parts.append(div(rows_html, _id='results.breakdown_card', _sn='Card', _tag='tr', background=WHITE, border=f'1px solid {BORDER}', border_radius=24, box_shadow=SH_SM, padding='4px 16px'))
    parts.append(text('Experimental tool, not a certified safety decision.', 13, 18, 400, MUTED, _id='results.footer_note', text_align='center', padding='0 8px'))
    ftr = btn('primary', 'Start another check', 'results.start_another_button')
    return lambda sc: phone(hdr, ''.join(parts), ftr, scroll=sc, bg=SUNKEN, body_pad='16px 16px 12px', body_gap=14, fade=True)


add('results', 'safe', results('safe'))
add('results', 'not_safe_row_expanded', results('unsafe'))
add('results', 'partially_checked', results('partial'))
add('results', 'not_enough_information', results('insufficient'))
add('results', 'notices', results('safe', notices=True))
add('results', 'notices_scrolled', results('safe', notices=True), scroll_to='results.history_notice')
add('results', 'safe_scrolled_to_end', results('safe'), scroll_to='results.footer_note')

# ======================= History =======================
VERDICTS = {'safe': ('Safe to Tow', 'pass', 'check_circle'), 'over': ('Over Limit', 'fail', 'x_circle'),
            'partial': ('Partially Checked', 'partial', 'info_circle'), 'info': ('Not Enough Info', 'notchecked', 'info_circle')}


def hist_card(rig, date, v, ids):
    I = (lambda n: n) if ids else (lambda n: None)
    t, k, ic = VERDICTS[v]
    return card(col(h_out(rig, 18, 22, 700, _id=I('history.entry_rig')) + text(date, 13, 18, 400, MUTED, _id=I('history.entry_date')), gap=2, flex_grow=1)
                + badge(t, k, I('history.entry_verdict'), ic), _id=I('history.entry_card'), display='flex', align_items='center', gap=12, padding='14px 16px', min_height=72)


def history(kind='few'):
    hdr = header('Check History', back='history.back', title_id='history.title')
    parts = [text('Every check you have run and where you stood.', 16, 22, 400, MUTED, _id='history.subtitle')]
    if kind == 'empty':
        parts.append(div(logo_img(56, 14) + text('No checks yet. Finish a check and it will be listed here.', 16, 22, 400, INK, _id='history.empty'), _sn='EmptyState', _tag='tr', display='flex', align_items='center', gap=14,
                         border=f'2px dashed {BORDER_STRONG}', border_radius=24, padding='20px 16px', background=SUNKEN))
    else:
        if kind == 'limit':
            parts.append(col(notice('The Free plan keeps your last 10 checks, and the oldest drops off as you add more. Pro keeps your last 100.', 'info', 'history.limit_notice')
                             + btn('ghost', 'Upgrade to Pro', 'history.upgrade_button', h=48, full=False, size=15), gap=2))
        entries = [('Summer rig', 'Oct 27, 2026', 'safe'), ('Weekend hauler', 'Oct 20, 2026', 'over'), ('Old faithful', 'Oct 3, 2026', 'partial'),
                   ('Summer rig', 'Sep 14, 2026', 'safe'), ('Weekend hauler', 'Aug 30, 2026', 'info'), ('Old faithful', 'Aug 2, 2026', 'safe'), ('Summer rig', 'Jul 19, 2026', 'over')]
        parts.append(col(''.join(hist_card(r, d, v, ids=(k == 0)) for k, (r, d, v) in enumerate(entries)), gap=10))
    return lambda sc: phone(hdr, ''.join(parts), body_pad='20px 16px 0', fade=True)


add('history', 'few_entries', history('few'))
add('history', 'limit_notice', history('limit'))
add('history', 'empty', history('empty'))

# ======================= Paywall =======================
def toast(msg):
    return div(text(msg, 15, 20, 500, WHITE), _id='paywall.toast', _sn='Snackbar', position='absolute', left=16, right=16, bottom=148, background=INK, border_radius=14, padding='14px 16px', box_shadow=SH_MD)


def offer_pro(busy=False):
    return div(col(h_out('RigCheck Pro', 22, 28, 800, PURPLE_DEEP, _id='paywall.offer_title') + text('One-time purchase, yours to keep, with a starter bundle of scans.', 15, 21, 400, INK, _id='paywall.offer_description'), gap=4)
               + btn('primary', '$24.99', 'paywall.buy_button', disabled=busy), _id='paywall.offer_card', _sn='Card/Offer', _tag='tr', display='flex', flex_direction='column', gap=16,
               background=TINT_PURPLE, border=f'1.5px solid {PURPLE_DEEP}', border_radius=24, padding=20)


def offer_pack(title, desc, price, ids, busy=False):
    I = (lambda n: n) if ids else (lambda n: None)
    return card(col(h_out(title, 18, 22, 700, _id=I('paywall.offer_title')) + text(desc, 14, 20, 400, MUTED, _id=I('paywall.offer_description')), gap=2, flex_grow=1, min_width=0)
                + btn('primary', price, I('paywall.buy_button'), h=48, full=False, size=16, disabled=busy), _id=I('paywall.offer_card'), display='flex', align_items='center', gap=12, padding='14px 16px')


def paywall(kind='free', busy=False, toast_msg=None):
    pro = kind.startswith('pro')
    hdr = header('Get More Scans' if pro else 'Unlock Pro', back='paywall.back', title_id='paywall.title')
    parts = [notice('<b>Beta: test payments. Every purchase uses a test card; no real money moves.</b>', 'scan', 'paywall.beta_label'),
             row(text('Buying for ' + EMAIL, 14, 20, 400, MUTED, _id='paywall.account_label', flex_grow=1, min_width=0, overflow='hidden', text_overflow='ellipsis', white_space='nowrap')
                 + btn('ghost', 'Sign out', 'paywall.sign_out_button', icn='logout', h=48, full=False, size=15, disabled=busy), gap=8)]
    if kind != 'plan_unknown':
        parts.append(div(badge('Pro plan' if pro else 'Free plan', 'plan', 'paywall.plan_label'), align_self='flex-start'))
    parts.append(text(('You have 12 scans left. Buy more scans any time. ' if pro else 'You have 3 scans left. Pro is a one-time purchase, yours to keep, and comes with a starter bundle of scans. ')
                      + 'Claude reads your truck tag, trailer tag, or scale ticket for you.', 15, 22, 400, INK, _id='paywall.explainer'))
    if kind == 'loading':
        parts.append(div(spinner(40, _id='paywall.loading'), display='flex', justify_content='center', padding='24px 0'))
    elif kind == 'load_error':
        parts.append(notice("Couldn't load offers: Network request failed", 'error', 'paywall.load_error'))
    elif kind == 'plan_unknown':
        parts.append(col(text('Checking your plan before showing what you can buy.', 15, 22, 400, INK, _id='paywall.plan_unknown') + btn('secondary', 'Try again', 'paywall.retry_button', h=48, full=False, size=15), gap=10))
    elif kind == 'free':
        parts.append(offer_pro(busy))
    elif kind == 'free_no_pro':
        parts.append(notice("Pro isn't available to buy right now.", 'info', 'paywall.no_pro'))
    elif kind == 'pro_bought':
        parts.append(col(text('Pro is yours. Updating your plan to show scan packs.', 15, 22, 400, INK, _id='paywall.pro_bought') + btn('secondary', 'Try again', 'paywall.retry_button', h=48, full=False, size=15), gap=10))
    elif kind == 'pro_no_packs':
        parts.append(notice('No scan packs are available right now.', 'info', 'paywall.no_packs'))
    else:
        parts.append(col(offer_pack('10 Scans', 'Good for a few rigs.', '$4.99', True, busy) + offer_pack('30 Scans', 'Best for a season of checks.', '$9.99', False, busy)
                         + offer_pack('100 Scans', 'For the whole fleet.', 'CA$12.99 one time', False, busy), gap=12))
    ftr = btn('ghost', 'Restore purchase', 'paywall.restore_button', disabled=busy)
    return lambda sc: phone(hdr, ''.join(parts), ftr, scroll=sc, body_pad='20px 16px 0', body_gap=16, overlay_html=toast(toast_msg) if toast_msg else '')


add('paywall', 'free_pro_offer', paywall('free'))
add('paywall', 'free_busy', paywall('free', busy=True))
add('paywall', 'free_no_pro', paywall('free_no_pro'))
add('paywall', 'pro_packs', paywall('pro', toast_msg='Purchase complete!'))
add('paywall', 'pro_no_packs', paywall('pro_no_packs'))
add('paywall', 'pro_bought_waiting', paywall('pro_bought'))
add('paywall', 'loading', paywall('loading'))
add('paywall', 'load_error', paywall('load_error'))
add('paywall', 'plan_unknown', paywall('plan_unknown'))

# ======================= Account =======================
def account(mode='sign_in', error=None, info=None, busy=False, keyboard=False, apple=False, focus=None, no_mail=False):
    create = mode == 'create'
    hdr = header('Create your account' if create else 'Sign in', back='account.back', title_id='account.title')
    parts = [text('Sign in or create an account to buy scans. Your purchases and scan balance follow your account to every device.', 16, 22, 400, MUTED, _id='account.reason'),
             field('Email', 'dana.rivera@example.com' if (busy or error or focus == 'email') else '', '', 'focus' if focus == 'email' else ('error' if error else 'default'), _id='account.email_field', placeholder='', caret=focus == 'email'),
             field('Password', 'secret1' if (busy or error) else '', '', 'error' if error else 'default', _id='account.password_field', password=True,
                   help='At least 6 characters' if create else '')]
    if error:
        parts.append(text(error, 14, 20, 500, DANGER_TEXT, _id='account.error'))
    if info:
        parts.append(notice(info, 'scan', 'account.info'))
    parts.append(btn('primary', 'Create account' if create else 'Sign in', 'account.submit_button', disabled=busy and False) if not busy else btn('primary', 'Please wait…', 'account.submit_button', disabled=True))
    parts.append(row(btn('ghost', 'Have an account? Sign in' if create else 'New here? Create an account', 'account.toggle_mode', h=48, full=False, size=15, disabled=busy)
                     + ('' if create else btn('ghost', 'Forgot password?', 'account.forgot_password', h=48, full=False, size=15, disabled=busy)), gap=4, justify_content='space-between', flex_wrap='wrap'))
    parts.append(div('', _id='account.divider', _sn='Divider', height=1, background=BORDER))
    google = btn('secondary', 'Continue with Google', 'account.google_button', disabled=busy)
    google = google.replace('</button>', '</button>', 1)
    parts.append(google)
    if apple:
        parts.append(btn('secondary', 'Continue with Apple', 'account.apple_button'))
    parts.append(col(btn('ghost', 'Send feedback', 'account.feedback_link', h=48, full=False, size=15)
                     + (text('This phone has no email app. Write to WTIAppDev@gmail.com instead.', 13, 18, 400, MUTED, _id='account.feedback_no_mail', text_align='center') if no_mail else ''),
                     gap=2, align_items='center'))
    ftr = btn('ghost', 'Not now', 'account.not_now_button', disabled=busy)
    return lambda sc: phone(hdr, ''.join(parts), ftr, scroll=sc, keyboard=keyboard, body_pad='20px 16px 0', body_gap=14, fade=not keyboard)


add('account', 'sign_in', account('sign_in'))
add('account', 'create_account', account('create'))
add('account', 'error', account('sign_in', error='That email and password do not match.'))
add('account', 'info_reset_sent', account('sign_in', info='If that email has an account, a reset link is on its way.'))
add('account', 'busy', account('sign_in', busy=True))
add('account', 'keyboard_open', account('sign_in', keyboard=True, focus='email'))
add('account', 'feedback_no_mail', account('sign_in', no_mail=True))
add('account', 'apple_enabled_future', account('sign_in', apple=True))

# ======================= Dialogs =======================
def over_picker(inner_fn):
    return lambda sc: with_overlay(picker('in')(0), inner_fn)


def over_chooser(inner):
    return lambda sc: with_overlay(chooser('truck')(0), inner)


photo = dialog('Scan Photo', 'Take a new photo, or choose one you already have?',
               btn('primary', 'Take Photo', 'photo_dialog.camera', 'camera', h=52) + btn('secondary', 'Choose from Gallery', 'photo_dialog.gallery', h=52), 'photo_dialog.title', 'photo_dialog.body')
add('photo_source_dialog', 'default', over_chooser(photo))


def scan_err(msg, steps):
    b = ''.join(btn('primary' if k == 0 else 'secondary', t, 'scan_error.next_step_button' if k == 0 else None, h=52) for k, t in enumerate(steps))
    b += btn('ghost', 'OK', 'scan_error.ok_button', h=52)
    return dialog('Scan failed', msg, b, 'scan_error.title', 'scan_error.message')


add('scan_error_dialog', 'message_only', over_chooser(scan_err('Something went wrong with that Scan, and we can\'t tell whether a Scan Credit was used. Check your Scan balance before you try again.', [])))
add('scan_error_dialog', 'one_next_step', over_chooser(scan_err("You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself.", ['Buy more Scans'])))
add('scan_error_dialog', 'two_next_steps', over_chooser(scan_err("We couldn't use that photo. Try a different photo, or type the numbers in yourself. Nothing was used.", ['Type it in', 'Choose a different photo'])))
add('scan_error_dialog', 'long_message', over_chooser(scan_err("We couldn't read that photo, and couldn't refund your Scan Credit automatically. Trying this photo again won't charge you again. If it keeps happening, contact support.", ['Try again'])))
late = dialog('A Scan finished late', "A Scan finished after you left that check, so its result wasn't used. It used a Scan Credit.", btn('ghost', 'OK', 'late_scan.ok_button', h=52), 'late_scan.title', 'late_scan.message')
add('late_scan_dialog', 'credit_used', lambda sc: with_overlay(picker('in')(0), late))


# ======================= Delete-Rig dialog and crash-report dialog (follow-up round) =======================
def delete_dialog(state):
    nick = 'Summer rig'
    deleting = state == 'deleting'
    inner = h_out(f'Delete "{nick}"?', 22, 28, 700, _id='delete_rig.title') + text("This frees its spot in your Garage and can't be undone.", 16, 24, 400, INK, _id='delete_rig.body')
    if state == 'delete_failed':
        inner += text(f'We couldn\'t delete "{nick}". It\'s still in your Garage; please try again.', 14, 20, 500, DANGER_TEXT, _id='delete_rig.error')
    inner += col(btn('destructive', 'Deleting\u2026' if deleting else 'Yes, delete', 'delete_rig.confirm_button', disabled=deleting, h=52)
                 + btn('ghost', 'Cancel', 'delete_rig.cancel_button', disabled=deleting, h=52), gap=8, margin_top=8)
    return modal(inner, 'delete_rig.dialog')


for _st in ('question', 'deleting', 'delete_failed'):
    add('delete_rig_dialog', _st, (lambda st: (lambda sc: with_overlay(picker('in')(0), delete_dialog(st))))(_st))


def crash_dialog(no_mail):
    if no_mail:
        inner = (text('This phone has no email app. Write to WTIAppDev@gmail.com instead.', 16, 24, 400, INK, _id='crash_prompt.no_mail_app')
                 + col(btn('ghost', 'OK', 'crash_prompt.dismiss_button', h=52), gap=8, margin_top=8))
    else:
        inner = (h_out('RigCheck closed unexpectedly last time. Send details?', 22, 28, 700, _id='crash_prompt.question')
                 + text('It holds the error, the app version, your Android version and phone model. Nothing about your account or your rigs. Nothing is sent unless you tap Send.', 14, 20, 400, MUTED, _id='crash_prompt.details')
                 + col(btn('primary', 'Send', 'crash_prompt.send_button', h=52) + btn('ghost', 'Not now', 'crash_prompt.dismiss_button', h=52), gap=8, margin_top=8))
    return modal(inner, None)


add('crash_report_dialog', 'question', lambda sc: with_overlay(picker('in')(0), crash_dialog(False)))
add('crash_report_dialog', 'no_email_app', lambda sc: with_overlay(picker('in')(0), crash_dialog(True)))
