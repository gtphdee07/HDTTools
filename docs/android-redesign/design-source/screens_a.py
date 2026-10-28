"""Rig picker, Chooser and the three entry screens."""
from lib import *

STATES = []
EMAIL = 'dana.rivera@example.com'


def add(screen, name, build, scroll_to=None, h=892):
    STATES.append(dict(screen=screen, name=name, build=build, scroll_to=scroll_to, h=h))


# ======================= Rig picker =======================
RIGS = [
    ('Summer rig', 'Ford F-450 · Jayco Eagle 32', 'Last checked 3 days ago', TINT_TEAL, TEAL_DEEP),
    ('Weekend hauler', 'Ram 3500 · Keystone Cougar', 'Last checked 2 weeks ago', TINT_PURPLE, PURPLE_DEEP),
    ('Old faithful', 'Chevy 2500 · Winnebago Micro', 'Last checked 3 months ago', TINT_ORANGE, ORANGE_DEEP),
]


def rig_card(nick, sub, last, bg, fg, ids):
    i = (lambda n: n) if ids else (lambda n: None)
    body = div(
        div(nick[0], _id=i('picker.rig_avatar'), display='flex', align_items='center', justify_content='center', width=52, height=52,
            border_radius=999, background=bg, color=fg, font_family=OUTFIT, font_weight=800, font_size=22, flex_shrink=0)
        + col(h_out(nick, 18, 22, 700, _id=i('picker.rig_nickname'))
              + text(sub, 14, 18, 400, MUTED, _id=i('picker.rig_subtitle'))
              + text(last, 12, 16, 400, MUTED, _id=i('picker.rig_last_checked')), gap=2, flex_grow=1, min_width=0)
        + icon('chevron_right', 24, MUTED),
        _sn='RigCardBody', display='flex', align_items='center', gap=14, flex_grow=1, min_width=0, padding='12px 8px 12px 16px', min_height=84, box_sizing='border-box')
    divider = div('', width=1, height=40, background=BORDER, flex_shrink=0)
    bin_ = icon_btn('trash', f'Delete {nick}', bg='transparent', color=MUTED, _id=i('picker.rig_delete_button'), margin_right=4)
    return card(body + divider + bin_, _id=i('picker.rig_card'), _tag='br', display='flex', align_items='center', gap=0, padding=0)


def picker(mode='in', menu=False, typing=False, no_mail=False):
    signed_in = mode == 'in'
    chip_text = '12 scans' if signed_in else '0 scans'
    hdr = header('RigCheck', brand=True, chip_html=chip(chip_text, 'picker.credit_chip'), account_html=account_row(EMAIL if signed_in else None))
    top = row(col(h_out('Which rig?', 28, 34, 800, _id='picker.heading', letter_spacing='-0.01em')
                  + text('Pick one you have checked before, or start a new one.', 16, 22, 400, MUTED, _id='picker.subheading'), gap=4, flex_grow=1)
              + btn('secondary', 'History', 'picker.history_button', 'clock', h=48, full=False, size=15), gap=12, align='flex-start')
    if signed_in:
        rigs = col(''.join(rig_card(*r, ids=(k == 0)) for k, r in enumerate(RIGS)), gap=12)
    else:
        rigs = div(logo_img(56, 14) + col(h_out('No saved rigs yet', 18, 22, 700) + text('Finish a check and your rig shows up here. Manual entry is free.', 14, 20, 400, MUTED), gap=2),
                   _id='picker.empty_state', _sn='EmptyState', _tag='tr', display='flex', align_items='center', gap=14, border=f'2px dashed {BORDER_STRONG}',
                   border_radius=24, padding='20px 16px', background=SUNKEN)
    name = 'Lakeside'
    create = btn('primary', 'Create', 'picker.create_button') if typing else btn('primary', 'Create', 'picker.create_button', disabled=True)
    panel = div(h_out('Or start a new rig', 18, 22, 700, PURPLE_DEEP, _id='picker.new_rig_label')
                + field_plain('Rig nickname', name if typing else '', 'focus' if typing else 'default', 'picker.new_rig_input', caret=typing)
                + create, _sn='Panel/Tint', _tag='tr', background=TINT_PURPLE, border_radius=24, padding=16, display='flex', flex_direction='column', gap=12)
    sheet = ''
    if menu:
        sheet = (scrim() + div(
            div('', align_self='center', width=40, height=4, border_radius=999, background=BORDER)
            + row(div(EMAIL[0].upper(), display='flex', align_items='center', justify_content='center', width=48, height=48, border_radius=999, background=PURPLE,
                      color=WHITE, font_family=OUTFIT, font_weight=700, font_size=20, flex_shrink=0)
                  + col(text('Signed in as', 12, 16, 400, MUTED) + h_out(EMAIL, 16, 22, 700, _id='picker.account_menu_email', overflow='hidden', text_overflow='ellipsis', white_space='nowrap'), gap=0, min_width=0),
                  gap=12, padding='4px 0 8px')
            + btn('destructive', 'Sign out', 'picker.sign_out_button', 'logout')
            + btn('ghost', 'Cancel', 'picker.account_menu_cancel'),
            _id='picker.account_menu', _sn='BottomSheet', _tag='tr', position='absolute', left=0, bottom=0, width=412, box_sizing='border-box', background=WHITE,
            border_radius='24px 24px 0 0', padding='12px 16px 64px', display='flex', flex_direction='column', gap=12, box_shadow=SH_MD))
    feedback = col(btn('ghost', 'Send feedback', 'picker.feedback_link', h=48, full=False, size=15)
                   + (text('This phone has no email app. Write to WTIAppDev@gmail.com instead.', 13, 18, 400, MUTED, _id='picker.feedback_no_mail', text_align='center') if no_mail else ''),
                   gap=2, align_items='center')
    body = top + rigs + panel + feedback
    return lambda sc: phone(hdr, body, overlay_html=sheet, keyboard=typing, body_pad='24px 16px 0', scroll=sc)


def field_plain(placeholder, value, state, _id, caret=False):
    border = f'2px solid {TEAL_DEEP}' if state == 'focus' else f'1.5px solid {BORDER_STRONG}'
    ring = '0 0 0 4px ' + TINT_TEAL if state == 'focus' else 'none'
    inner = (div(value + '<span style="display:inline-block;width:2px;height:22px;background:#087379;vertical-align:middle;margin-left:1px"></span>' if caret else (value or placeholder),
                 color=INK if value else MUTED, opacity=None if value else '0.85'))
    return div(inner, _id=_id, _sn='Field/Text', height=56, box_sizing='border-box', border=border, border_radius=8, padding='0 16px', display='flex', align_items='center',
               font_size=17, background=WHITE, box_shadow=ring)


add('rig_picker', 'in', picker('in'))
add('rig_picker', 'account_menu', picker('in', menu=True))
add('rig_picker', 'signed_out_empty', picker('out'))
add('rig_picker', 'feedback_no_mail', picker('in', no_mail=True), scroll_to='picker.feedback_no_mail')
add('rig_picker', 'new_rig_typing', picker('in', typing=True), scroll_to='picker.new_rig_input')

# ======================= Chooser =======================
MODS = {
    'truck': ('Truck Tag', "How do you want to enter your truck's compliance-label values?", 1),
    'trailer': ('Trailer Tag', "How do you want to enter your trailer's compliance-label values?", 2),
    'scale': ('Scale Ticket', 'How do you want to enter your CAT Scale ticket values?', 3),
}


def choice(kind):
    scan = kind == 'scan'
    bg, bd, circ, fg = (TINT_PURPLE, PURPLE_DEEP, PURPLE, WHITE) if scan else (TINT_TEAL, TEAL_DEEP, TEAL, INK)
    return (f'<button{attrs("chooser.scan_card" if scan else "chooser.manual_card", st(width="100%", box_sizing="border-box", min_height=148, padding=16, border=f"1.5px solid {bd}", border_radius=24, background=bg, color=INK, box_shadow=SH_SM, display="flex", align_items="center", gap=16, text_align="left"), None, "Card/Option", "tr")}>'
            + div(icon('camera' if scan else 'keyboard', 32, fg), display='flex', align_items='center', justify_content='center', width=64, height=64, border_radius=999, background=circ, flex_shrink=0)
            + col(row(h_out('Scan Photo' if scan else 'Enter Manually', 20, 24, 700) + badge('1 credit' if scan else 'Free', 'credit' if scan else 'free', 'chooser.scan_badge' if scan else 'chooser.manual_badge'), gap=8, flex_wrap='wrap')
                  + text('Photograph the label — Claude reads the fields for you.' if scan else 'Type the values in yourself — free, no photo, works offline.', 15, 21, 400, MUTED), gap=6, align_items='flex-start', flex_grow=1)
            + '</button>')


def chooser(mod='truck', flight=False, chip_text='12 scans', dialog_html=''):
    title, prompt, n = MODS[mod]
    hdr = header(title, back='chooser.back', chip_html=chip(chip_text, 'chooser.credit_chip'), step_html=step_indicator(n, 'chooser.step_bar'), title_id='chooser.title')
    body = (h_out(prompt, 22, 28, 700, _id='chooser.prompt') + choice('scan') + choice('manual')
            + div(icon('info_circle', 22, MUTED) + text('This same choice appears again before the trailer tag and scale ticket screens.', 14, 20, 400, MUTED, _id='chooser.footer_note'),
                  display='flex', align_items='flex-start', gap=10, background=SUNKEN, border_radius=14, padding='12px 14px'))
    over = ''
    if flight:
        over = div(spinner(48) + h_out('Reading…', 20, 24, 700, _id='chooser.loading_text'), _id='chooser.loading_overlay', _sn='Overlay/Scan', position='absolute', left=0, top=0, width=412, height=892,
                   background='rgba(255,255,255,0.88)', display='flex', flex_direction='column', align_items='center', justify_content='center', gap=16, _a={'data-scrim': '1'})
    return lambda sc: phone(hdr, body, overlay_html=over or dialog_html, body_pad='24px 16px 0', scroll=sc)


add('chooser', 'truck', chooser('truck'))
add('chooser', 'trailer', chooser('trailer'))
add('chooser', 'scale', chooser('scale'))
add('chooser', 'scan_in_flight', chooser('truck', flight=True))
add('chooser', 'balance_loading', chooser('truck', chip_text='…'))

# ======================= Entry screens =======================


def label_mock(lines, focus, hint_id, img_id, hint_text, tag_name, placeholder=True, badge_id=None):
    ln = []
    lo = 0 if focus is None else max(0, min(focus - 1, len(lines) - 3))
    for i, t in list(enumerate(lines))[lo:lo + 3]:
        on = i == focus
        ln.append(div(t, padding='3px 8px', border_radius=8, font_size=13 if not on else 14, line_height=18, font_weight=700 if on else 400,
                      color=INK if on else MUTED, background=TINT_ORANGE if on else None, border=f'2.5px solid {ORANGE}' if on else '2.5px solid transparent'))
    mock = div(''.join(ln) + (div('Placeholder crop: the real label photo goes here', padding='3px 10px', background='rgba(22,19,31,0.68)', color=WHITE, font_size=11, line_height=14, position='absolute', left=0, right=0, bottom=0) if placeholder else ''),
               _id=img_id, _sn='ReferenceCrop', position='relative', background='#e9f0f3', border=f'1px solid {BORDER}', border_radius=14, padding='8px 8px 22px', overflow='hidden')
    cap = row(icon('search', 20, TEAL_DEEP) + text(hint_text, 14, 20, 400, MUTED, _id=hint_id, flex_grow=1)
              + (badge(tag_name, 'plan', badge_id) if tag_name else ''), gap=8)
    return div(cap + mock, _sn='ReferenceCard', _tag='tr', background=WHITE, border=f'1px solid {BORDER}', border_radius=24, padding=12, box_shadow=SH_MD, display='flex', flex_direction='column', gap=10, flex_shrink=0, _a={'data-region': 'header'}, margin='12px 16px 0')


def slider(pct=20):
    left = (pct - 15) / 10 * 100
    return div(div('', position='absolute', left=0, right=0, top=22, height=4, border_radius=999, background=BORDER)
               + div('', position='absolute', left=0, top=22, width=f'{left}%', height=4, border_radius=999, background=TEAL_DEEP)
               + div('', position='absolute', left=f'calc({left}% - 14px)', top=10, width=28, height=28, border_radius=999, background=WHITE, border=f'3px solid {TEAL_DEEP}', box_sizing='border-box'),
               _id='truck.pin_weight_slider', _sn='Slider', position='relative', height=48)


TRUCK_LINES = ['MFD. BY [MAKER]      DATE: 09/24', 'GVWR: 6350 KG (14000 LB)', 'FRONT GAWR: 2722 KG (6000 LB)', 'REAR GAWR: 4491 KG (9900 LB)']
TRAILER_LINES = ['MFD. BY [MAKER]      DATE: 05/22', 'GVWR: 5438 KG (11990 LB)', 'GAWR EACH AXLE: 3175 KG (7000 LB)', 'UVW: [see tag]']


def truck(filled=False, focus=None, notice_on=False, gcwr_warn=False, info=False, standalone='blank', scanning=False, keyboard=False, scroll_to=None, focus_idx=None):
    v = (lambda x: x if filled else '')
    fs = lambda key: 'focus' if focus == key else 'default'
    cr = lambda key: focus == key
    hdr = header('Truck Tag', back='truck.back', chip_html=chip('12 scans', 'truck.credit_chip'), step_html='' if keyboard else step_indicator(1, 'truck.step_bar'), title_id='truck.title', pad_bottom=12 if keyboard else 16)
    hint = 'Tap a field to see its spot on the tag'
    pinned = label_mock(TRUCK_LINES, focus_idx, 'truck.reference_hint', 'truck.reference_image', hint, {'gvwr': 'GVWR', 'front': 'Front GAWR', 'rear': 'Rear GAWR'}.get(focus), badge_id='truck.reference_focus_badge')
    parts = []
    if notice_on:
        parts.append(notice('A Scan was used, but we couldn’t read: Rear GAWR and GCWR. Type them in, or go back and choose a different photo.'.replace('’', "'"), 'scan', 'truck.scan_notice'))
    parts.append(text("Find these values on your truck's compliance label (usually inside the driver door jamb).", 16, 22, 400, MUTED, _id='truck.instructions'))
    parts.append(field('Description', v('Ford F-450'), '', fs('desc'), placeholder='e.g. Ford F-450', _id='truck.description_field', caret=cr('desc')))
    parts.append(field('Name', v('Daily driver'), '', fs('name'), _id='truck.name_field', caret=cr('name')))
    parts.append(field('GVWR, lb', v('14,000'), 'lb', fs('gvwr'), _id='truck.gvwr_field', caret=cr('gvwr')))
    parts.append(field('Front GAWR, lb', v('6,000'), 'lb', fs('front'), _id='truck.front_gawr_field', caret=cr('front')))
    parts.append(field('Rear GAWR, lb', v('9,900'), 'lb', fs('rear'), _id='truck.rear_gawr_field', caret=cr('rear')))
    g = col(field('GCWR, lb — optional', '12,000' if gcwr_warn else v('26,000'), 'lb', 'default', _id='truck.gcwr_field')
            + text("From your owner's manual. Leave blank if you can't find it.", 13, 18, 400, MUTED, _id='truck.gcwr_help')
            + (text("This is lower than your GVWR. Check it against your owner's manual. We'll still use it.", 13, 18, 500, ORANGE_DEEP, _id='truck.gcwr_warning') if gcwr_warn else ''), gap=6)
    parts.append(g)
    sa_filled = standalone == 'filled'
    panel_parts = [h_out("Don't know your tow vehicle's stand-alone weight?", 18, 22, 700, ORANGE_DEEP, _id='truck.standalone_panel_title'),
                   text("Scan a CAT Scale ticket weighing just your tow vehicle (no trailer attached) and we'll fill in the field above for you.", 14, 20, 400, MUTED, _id='truck.standalone_panel_body')]
    if scanning:
        panel_parts.append(btn('secondary', 'Reading…', 'truck.scan_standalone_button', disabled=True, h=52, size=16))
    else:
        panel_parts.append(btn('secondary', 'Scan tow-vehicle-only ticket', 'truck.scan_standalone_button', 'camera', h=52, size=16))
    panel_parts.append(row(label_caps('Stand-alone weight, lb — optional', _id='truck.standalone_label', flex_grow=1)
                           + icon_btn('info_circle', 'What is stand-alone weight?', bg='transparent', color=TEAL_DEEP, _id='truck.standalone_info', margin='-8px -8px -8px 0'), gap=4))
    if info:
        panel_parts.append(text("If left blank, we'll assume the trailer axle reading is 80% of the trailer's total weight. Fill this in for a more accurate pin-weight estimate.", 13, 18, 400, INK, _id='truck.standalone_info_text',
                                background=WHITE, padding='10px 12px', border_radius=8))
    panel_parts.append(field_box('8,700' if sa_filled else '', 'lb', 'default', 'truck.standalone_field'))
    if not sa_filled:
        panel_parts.append(text("No ticket? Estimate pin/hitch weight as 20% of the trailer's weight", 14, 20, 500, INK, _id='truck.pin_weight_label'))
        panel_parts.append(slider(20))
        panel_parts.append(text('Industry recommendations are typically 15-25% — we default to 20%.', 12, 16, 400, MUTED, _id='truck.pin_weight_caption'))
    parts.append(div(''.join(panel_parts), _id='truck.standalone_panel', _sn='Panel/Tint', _tag='tr', background=TINT_ORANGE, border_radius=24, padding=16, display='flex', flex_direction='column', gap=12))
    ftr = btn('primary', 'Next: Trailer Tag', 'truck.next_button', 'forward')
    return lambda sc: phone(hdr + pinned, ''.join(parts), ftr, scroll=sc, keyboard=keyboard, body_gap=14, body_pad='16px 16px 12px', fade=not keyboard)


add('truck_tag_entry', 'blank', truck())
add('truck_tag_entry', 'filled', truck(filled=True, focus='gvwr', focus_idx=1), scroll_to='truck.gvwr_field')
add('truck_tag_entry', 'scan_notice', truck(notice_on=True, filled=True, focus_idx=None))
add('truck_tag_entry', 'gcwr_warning', truck(filled=True, gcwr_warn=True, focus_idx=None), scroll_to='truck.gcwr_field')
add('truck_tag_entry', 'standalone_blank', truck(filled=True), scroll_to='truck.standalone_panel')
add('truck_tag_entry', 'standalone_pin_weight', truck(filled=True), scroll_to='truck.pin_weight_caption')
add('truck_tag_entry', 'standalone_info', truck(filled=True, info=True), scroll_to='truck.standalone_panel')
add('truck_tag_entry', 'standalone_filled', truck(filled=True, standalone='filled'), scroll_to='truck.standalone_panel')
add('truck_tag_entry', 'standalone_scan_in_flight', truck(filled=True, scanning=True), scroll_to='truck.standalone_panel')
add('truck_tag_entry', 'keyboard_open', truck(filled=True, focus='front', keyboard=True, focus_idx=2), scroll_to='truck.front_gawr_field')


def trailer(filled=False, focus=None, notice_on=False, keyboard=False, focus_idx=None):
    v = (lambda x: x if filled else '')
    fs = lambda key: 'focus' if focus == key else 'default'
    hdr = header('Trailer Tag', back='trailer.back', chip_html='', step_html='' if keyboard else step_indicator(2, 'trailer.step_bar'), title_id='trailer.title', pad_bottom=12 if keyboard else 16)
    pinned = label_mock(TRAILER_LINES, focus_idx, 'trailer.reference_hint', 'trailer.reference_image', 'Tap a field to see its spot on the tag',
                        {'gvwr': 'GVWR', 'gawr': 'GAWR per axle', 'uvw': 'UVW'}.get(focus), badge_id='trailer.reference_focus_badge')
    parts = []
    if notice_on:
        parts.append(notice("A Scan was used, but we couldn't read: GAWR per axle. Type it in, or go back and choose a different photo.", 'scan', 'trailer.scan_notice'))
    parts.append(text("Find these values on your trailer's compliance label (usually near the front, curb side).", 16, 22, 400, MUTED, _id='trailer.instructions'))
    parts.append(field('Description', v('Brinkley RV'), '', fs('desc'), placeholder='e.g. Brinkley RV', _id='trailer.description_field'))
    parts.append(field('Name', v('Weekender'), '', fs('name'), _id='trailer.name_field'))
    parts.append(field('GVWR, lb', v('11,990'), 'lb', fs('gvwr'), _id='trailer.gvwr_field', caret=focus == 'gvwr'))
    parts.append(field('GAWR per axle, lb', v('7,000'), 'lb', fs('gawr'), _id='trailer.gawr_field', caret=focus == 'gawr'))
    parts.append(col(field('Axle count — optional', v('2'), '', fs('axles'), _id='trailer.axle_count_field')
                     + text('Defaults to 2 if left blank.', 13, 18, 400, MUTED, _id='trailer.axle_count_help'), gap=6))
    parts.append(field('Unloaded weight (UVW), lb', v('8,400'), 'lb', fs('uvw'), _id='trailer.uvw_field', caret=focus == 'uvw'))
    ftr = btn('primary', 'Next: Scale Ticket', 'trailer.next_button', 'forward')
    return lambda sc: phone(hdr + pinned, ''.join(parts), ftr, scroll=sc, keyboard=keyboard, body_gap=14, body_pad='16px 16px 12px', fade=not keyboard)


add('trailer_tag_entry', 'blank', trailer())
add('trailer_tag_entry', 'filled', trailer(filled=True, focus='gawr', focus_idx=2), scroll_to='trailer.gawr_field')
add('trailer_tag_entry', 'scan_notice', trailer(notice_on=True, filled=True))
add('trailer_tag_entry', 'keyboard_open', trailer(filled=True, focus='uvw', keyboard=True, focus_idx=3), scroll_to='trailer.uvw_field')


def ticket_image():
    def tagpos(n, left, top):
        return div(str(n), position='absolute', left=left, top=top, width=24, height=24, border_radius=999, background=ORANGE, color=INK, font_family=OUTFIT, font_weight=800, font_size=13,
                   display='flex', align_items='center', justify_content='center', border=f'2px solid {WHITE}', box_sizing='border-box')
    lines = [('SCALE LOCATION', 'Truck stop, Exit 42'), ('STEER', '4,900'), ('DRIVE', '7,600'), ('TRAILER', '9,600'), ('GROSS', '22,100')]
    rows = ''.join(div(div(a) + div(b), display='flex', justify_content='space-between', padding='6px 12px 6px 38px', font_size=13, line_height=16, color=MUTED, border_bottom='1px dashed #c3ccd2') for a, b in lines)
    badges = ''.join(tagpos(i + 1, 8, 4 + i * 29 + 4) for i in range(5))
    return div(rows + badges + div('Placeholder: real ticket photo goes here, numbers drawn on it', padding='3px 10px', background='rgba(22,19,31,0.68)', color=WHITE, font_size=11, line_height=14),
               _id='scale.reference_image', _sn='ReferenceImage', position='relative', background='#eef2f4', border=f'1px solid {BORDER}', border_radius=14, overflow='hidden', padding_top=0)


def scale(filled=False, focus=None, notice_on=False, keyboard=False):
    v = (lambda x: x if filled else '')
    fs = lambda key: 'focus' if focus == key else 'default'
    hdr = header('Scale Ticket', back='scale.back', chip_html='', step_html='' if keyboard else step_indicator(3, 'scale.step_bar'), title_id='scale.title', pad_bottom=12 if keyboard else 16)
    legend = row(''.join(row(div(str(n), display='flex', align_items='center', justify_content='center', width=22, height=22, border_radius=999, background=ORANGE, color=INK, font_family=OUTFIT, font_weight=700, font_size=13) + span(t, font_size=14, font_weight=500), gap=6,
                             background=SUNKEN, border=f'1px solid {BORDER}', border_radius=999, padding='4px 10px 4px 4px') for n, t in [(1, 'Scale location'), (2, 'Steer'), (3, 'Drive'), (4, 'Trailer'), (5, 'Gross')]),
                 gap=6, flex_wrap='wrap', _id='scale.legend')
    parts = []
    if notice_on:
        parts.append(notice("A Scan was used, but we couldn't read: Trailer axle(s). Type it in, or go back and choose a different photo.", 'scan', 'scale.scan_notice'))
    parts += [text('Find these values on your CAT Scale printout.', 16, 22, 400, MUTED, _id='scale.instructions'), ticket_image(), legend,
              field('Scale location', v('Truck stop, Exit 42'), '', fs('loc'), _id='scale.location_field', num_badge=1),
              field('Steer axle, lb', v('4,900'), 'lb', fs('steer'), _id='scale.steer_field', num_badge=2, caret=focus == 'steer'),
              field('Drive axle, lb', v('7,600'), 'lb', fs('drive'), _id='scale.drive_field', num_badge=3),
              field('Trailer axle(s), lb', v('9,600'), 'lb', fs('trailer'), _id='scale.trailer_field', num_badge=4),
              field('Gross weight, lb', v('22,100'), 'lb', fs('gross'), _id='scale.gross_field', num_badge=5)]
    ftr = btn('primary', 'Check Weights', 'scale.check_button')
    return lambda sc: phone(hdr, ''.join(parts), ftr, scroll=sc, keyboard=keyboard, body_gap=14, body_pad='16px 16px 12px', fade=not keyboard)


add('scale_ticket_entry', 'blank', scale())
add('scale_ticket_entry', 'filled', scale(filled=True), scroll_to='scale.location_field')
add('scale_ticket_entry', 'scan_notice', scale(notice_on=True, filled=True))
add('scale_ticket_entry', 'keyboard_open', scale(filled=True, focus='steer', keyboard=True), scroll_to='scale.steer_field')
