"""Component library for the RigCheck Android redesign. Every function returns an HTML string.

Elements that map to an inventory id carry data-id (and data-style, the component name). The build
step reads those back from the rendered page to measure size and region for the map.
"""
INK = '#16131f'
MUTED = '#55506a'
TEAL = '#12b5ae'
TEAL_DEEP = '#087379'
PURPLE = '#7b3fe4'
PURPLE_DEEP = '#5b25b8'
ORANGE = '#ff7a1a'
ORANGE_DEEP = '#b84a00'
PINE = '#3f6b35'
DANGER = '#b5473a'
DANGER_TEXT = '#9a3a2e'
SLATE = '#576775'
SUNKEN = '#f4f8f9'
BORDER = '#d5dee3'
BORDER_STRONG = '#738490'
TINT_TEAL = '#e3f7f5'
TINT_PURPLE = '#f1ecff'
TINT_ORANGE = '#fff0e1'
TINT_RED = '#f8e6e3'
TINT_GREEN = '#e8f0e5'
WHITE = '#ffffff'
LOGO = '/_blob/13ba8534e28291e82131a15e757e31f1'
OUTFIT = "'Outfit', system-ui, sans-serif"
BODY = "'DM Sans', system-ui, sans-serif"
SH_SM = '0 1px 3px rgba(22,19,31,0.10)'
SH_MD = '0 8px 24px rgba(22,19,31,0.12)'
UNITLESS = {'font-weight', 'line-height', 'opacity', 'flex-grow', 'flex-shrink', 'flex', 'z-index', 'order'}
LOGO_URL = {'v': LOGO}


def st(**k):
    parts = []
    for key, v in k.items():
        key = key.replace('_', '-')
        if v is None:
            continue
        if isinstance(v, (int, float)) and v != 0 and (key not in UNITLESS or (key == 'line-height' and v > 4)):
            v = f'{v}px'
        parts.append(f'{key}:{v}')
    return ';'.join(parts)


def attrs(_id=None, style=None, a=None, style_name=None, tag=None):
    out = ''
    if _id:
        out += f' data-id="{_id}"'
    if style_name:
        out += f' data-style="{style_name}"'
    if tag:
        out += f' data-tag="{tag}"'
    if a:
        for k, v in a.items():
            out += f' {k}="{v}"'
    if style:
        out += f' style="{style}"'
    return out


def div(content='', _id=None, _sn=None, _tag=None, _a=None, **style):
    return f'<div{attrs(_id, st(**style), _a, _sn, _tag)}>{content}</div>'


def span(content='', _id=None, _sn=None, _a=None, **style):
    return f'<span{attrs(_id, st(**style), _a, _sn)}>{content}</span>'


def row(content, gap=8, align='center', _id=None, **style):
    return div(content, _id, display='flex', align_items=align, gap=gap, **style)


def col(content, gap=8, _id=None, _sn=None, **style):
    return div(content, _id, _sn, display='flex', flex_direction='column', gap=gap, **style)


ICONS = {
    'camera': '<path d="M4 8h3l1.5-2h7L17 8h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    'chevron_down': '<path d="m6 9 6 6 6-6"/>',
    'chevron_up': '<path d="m6 15 6-6 6 6"/>',
    'chevron_right': '<path d="m9 6 6 6-6 6"/>',
    'back': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    'forward': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 20c1-4 4-6 8-6s7 2 8 6"/>',
    'logout': '<path d="M10 4H5v16h5"/><path d="m16 8 4 4-4 4M20 12H9"/>',
    'check_circle': '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/>',
    'x_circle': '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    'info_circle': '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    'warning': '<path d="M12 3 2.5 20h19z"/><path d="M12 10v5M12 17.5h.01"/>',
    'search': '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.5-4.5"/>',
    'keyboard': '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10"/>',
    'receipt': '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
    'star': '<path d="m12 3 2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.5 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z"/>',
    'refresh': '<path d="M20 11a8 8 0 1 0-2 5.3M20 5v6h-6"/>',
    'close': '<path d="M6 6l12 12M18 6 6 18"/>',
    'trash': '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
}


def icon(name, size=24, color='currentColor', sw=2, extra=''):
    return (f'<svg aria-hidden="true" viewBox="0 0 24 24" style="width:{size}px;height:{size}px;fill:none;stroke:{color};'
            f'stroke-width:{sw};stroke-linecap:round;stroke-linejoin:round;flex-shrink:0;{extra}">{ICONS[name]}</svg>')


def text(content, size=16, lh=22, weight=400, color=INK, family=BODY, _id=None, _sn=None, **style):
    return div(content, _id, _sn, font_family=family, font_size=size, line_height=lh, font_weight=weight, color=color, **style)


def h_out(content, size=18, lh=22, weight=700, color=INK, _id=None, **style):
    return text(content, size, lh, weight, color, OUTFIT, _id, **style)


def label_caps(content, _id=None, color=INK, **style):
    return text(content, 13, 16, 700, color, BODY, _id, letter_spacing='0.04em', **style)


# ---------- buttons ----------
def btn(kind, label, _id=None, icn=None, disabled=False, h=56, full=True, size=17, sn=None):
    base = dict(height=h, border_radius=999, display='flex', align_items='center', justify_content='center', gap=8,
                font_family=OUTFIT, font_size=size, box_sizing='border-box', cursor='pointer')
    if full:
        base['width'] = '100%'
    else:
        base['padding'] = '0 20px'
        base['flex_shrink'] = 0
    if disabled:
        base.update(background='#e4e0ee', color='#6a647c', border='none', font_weight=700)
        name = 'Button/Disabled'
    elif kind == 'primary':
        base.update(background=ORANGE, color=INK, border='none', font_weight=700, box_shadow=SH_SM)
        name = 'Button/Primary'
    elif kind == 'secondary':
        base.update(background=WHITE, color=TEAL_DEEP, border=f'1.5px solid {TEAL_DEEP}', font_weight=600)
        name = 'Button/Secondary'
    elif kind == 'ghost':
        base.update(background='transparent', color=TEAL_DEEP, border='none', font_weight=700)
        name = 'Button/Ghost'
    elif kind == 'destructive':
        base.update(background=WHITE, color=DANGER, border=f'1.5px solid {DANGER}', font_weight=700)
        name = 'Button/Destructive'
    else:
        raise ValueError(kind)
    content = (icon(icn, 22) if icn else '') + label
    return f'<button{attrs(_id, st(**base), {"disabled": "disabled"} if disabled else None, sn or name)}>{content}</button>'


def icon_btn(icn, label, bg='rgba(255,255,255,0.72)', color=INK, _id=None, size=48, **style):
    return (f'<button{attrs(_id, st(width=size, height=size, border="none", border_radius=999, background=bg, color=color, display="flex", align_items="center", justify_content="center", flex_shrink=0, **style), {"aria-label": label}, "IconButton/48")}>'
            f'{icon(icn, 24)}</button>')


# ---------- chips, badges ----------
def chip(txt, _id, label=None, bg=WHITE):
    label = label or f'Scan balance: {txt}. Opens the Paywall'
    return (f'<button{attrs(_id, st(height=48, padding="0 16px 0 12px", border="none", border_radius=999, background=bg, color=INK, display="flex", align_items="center", gap=8, font_family=OUTFIT, font_weight=700, font_size=17, box_shadow=SH_SM, flex_shrink=0, box_sizing="border-box"), {"aria-label": label}, "Chip/Credit")}>'
            f'{icon("camera", 26)}<span>{txt}</span></button>')


BADGES = {
    'credit': (PURPLE, WHITE, None),
    'free': (PINE, WHITE, None),
    'pass': (TINT_GREEN, PINE, None),
    'fail': (TINT_RED, DANGER_TEXT, None),
    'partial': (TINT_PURPLE, PURPLE_DEEP, None),
    'notchecked': (SUNKEN, MUTED, BORDER_STRONG),
    'plan': (TINT_TEAL, TEAL_DEEP, None),
}


def badge(txt, kind, _id=None, icn=None):
    bg, fg, bd = BADGES[kind]
    ic = icon(icn, 14, fg, 2.4) if icn else ''
    return span(ic + txt, _id, 'Badge', display='inline-flex', align_items='center', gap=4, background=bg, color=fg,
                border=f'1px solid {bd}' if bd else None, border_radius=999, padding='2px 10px', font_size=13,
                line_height=18, font_weight=700, white_space='nowrap')


# ---------- header ----------
def step_indicator(n, _id):
    def node(i, name):
        cur = i == n
        done = i < n
        circle = div(str(i),
                     display='flex', align_items='center', justify_content='center', width=32, height=32, border_radius=999,
                     box_sizing='border-box', font_family=OUTFIT, font_weight=700, font_size=15,
                     background=INK if (cur or done) else WHITE, color=WHITE if (cur or done) else INK,
                     border=None if (cur or done) else f'2px solid {INK}')
        return col(circle + div(name, font_size=13, line_height=16, font_weight=700 if cur else 400),
                   gap=4, align_items='center', width=64)

    line = div('', flex_grow=1, height=2, background=INK, margin_top=15, opacity='0.35')
    return col(
        div(f'Step {n} of 3', font_size=13, line_height=16, font_weight=700, letter_spacing='0.04em')
        + row(node(1, 'Truck') + line + node(2, 'Trailer') + line + node(3, 'Scale'), gap=0, align='flex-start'),
        gap=8, padding='0 4px', _id=_id, _sn='StepIndicator')


def header(title=None, back=None, chip_html='', sub=None, step_html='', brand=False, account_html='', title_id=None, pad_bottom=16, radius=True, sub_id=None):
    """Teal top app bar. back=None draws no back button; back='id' draws one with that id."""
    parts = []
    if brand:
        parts.append(row(
            f'<img{attrs("picker.logo", st(width=52, height=52, border_radius=14, border="2px solid #ffffff", object_fit="cover", flex_shrink=0), {"src": LOGO, "alt": "Wandering Trails, Wagging Tails"}, "Logo/52")}>'
            + col(h_out(title or 'RigCheck', 26, 30, 800, _id='picker.app_title', letter_spacing='-0.01em')
                  + div('Weight safety, before you roll', _id='picker.tagline', font_size=13, line_height=16), gap=0, flex_grow=1, min_width=0)
            + chip_html, gap=12))
    else:
        left = icon_btn('back', 'Back', _id=back) if back else ''
        t = ''
        if title:
            t = col(h_out(title, 26, 30, 800, _id=title_id, letter_spacing='-0.01em', margin=0)
                    + (div(sub, sub_id, font_size=13, line_height=16) if sub else ''), gap=0, flex_grow=1, min_width=0)
        parts.append(row(left + t + chip_html, gap=8))
    if account_html:
        parts.append(account_html)
    if step_html:
        parts.append(step_html)
    return (f'<div data-region="header"{attrs(None, st(background=TEAL, border_radius="0 0 24px 24px" if radius else 0, padding=f"36px 16px {pad_bottom}px", display="flex", flex_direction="column", gap=12 if brand else 14, box_shadow=SH_SM, flex_shrink=0))}>'
            + ''.join(parts) + '</div>')


def account_row(email=None):
    if email:
        initial = email[0].upper()
        return (f'<button{attrs("picker.account_status", st(height=48, width="100%", box_sizing="border-box", border="none", border_radius=14, background="rgba(255,255,255,0.72)", color=INK, padding="0 12px", display="flex", align_items="center", gap=12, text_align="left"), {"aria-label": f"Account: signed in as {email}. Opens account menu"}, "AccountStatus")}>'
                + div(initial, _id='picker.account_avatar', display='flex', align_items='center', justify_content='center', width=32, height=32, border_radius=999, background=PURPLE, color=WHITE, font_family=OUTFIT, font_weight=700, font_size=15, flex_shrink=0)
                + col(div('Signed in as', font_size=12, line_height=14) + div(email, font_size=14, line_height=18, font_weight=700, overflow='hidden', text_overflow='ellipsis', white_space='nowrap'), gap=0, flex_grow=1, min_width=0)
                + icon('chevron_down', 24) + '</button>')
    return (f'<button{attrs("picker.account_status", st(height=48, width="100%", box_sizing="border-box", border="none", border_radius=14, background="rgba(255,255,255,0.72)", color=INK, padding="0 12px", display="flex", align_items="center", gap=12, text_align="left"), {"aria-label": "Not signed in. Sign in"}, "AccountStatus")}>'
            + div(icon('user', 20), _id='picker.account_avatar', display='flex', align_items='center', justify_content='center', width=32, height=32, border_radius=999, background=WHITE, color=INK, flex_shrink=0)
            + div('Not signed in', font_size=14, line_height=18, font_weight=700, flex_grow=1)
            + div('Sign in', font_family=OUTFIT, font_weight=700, font_size=15, color=TEAL_DEEP, padding='0 4px')
            + icon('chevron_right', 24) + '</button>')


# ---------- fields ----------
def field(label, value='', unit='', state='default', help='', placeholder='', _id=None, caret=False, num_badge=None, disabled=False, password=False):
    border = {'default': f'1.5px solid {BORDER_STRONG}', 'focus': f'2px solid {TEAL_DEEP}', 'error': f'2px solid {DANGER}'}[state]
    ring = '0 0 0 4px ' + TINT_TEAL if state == 'focus' else 'none'
    shown = ('•' * len(value)) if password else value
    inner = (div(shown, color=INK if value else MUTED) if value else div(placeholder, color=MUTED, opacity='0.85'))
    if caret:
        inner = div(shown + '<span style="display:inline-block;width:2px;height:22px;background:#087379;vertical-align:middle;margin-left:1px"></span>', color=INK)
    box = div(inner + (div(unit, font_size=15, color=MUTED) if unit else ''), _sn='Field/Text', _id=_id,
              height=56, box_sizing='border-box', border=border, border_radius=8, padding='0 16px', display='flex', align_items='center',
              justify_content='space-between', font_size=17, background='#eeeaf3' if disabled else WHITE, box_shadow=ring, font_family=BODY, opacity='0.7' if disabled else None)
    nb = ''
    if num_badge:
        nb = div(str(num_badge), display='flex', align_items='center', justify_content='center', width=22, height=22, border_radius=999, background=ORANGE, color=INK, font_family=OUTFIT, font_weight=700, font_size=13, flex_shrink=0)
    lab = row(nb + label_caps(label), gap=8)
    return col(lab + box + (div(help, font_size=13, line_height=18, color=DANGER_TEXT if state == 'error' else MUTED) if help else ''), gap=6)


# ---------- notices / cards ----------
def notice(content, tone='info', _id=None, title=None, icn=None):
    bg, fg, ic = {'info': (SUNKEN, MUTED, 'info_circle'), 'scan': (TINT_ORANGE, ORANGE_DEEP, 'info_circle'),
                  'warn': (TINT_ORANGE, ORANGE_DEEP, 'warning'), 'error': (TINT_RED, DANGER_TEXT, 'info_circle')}[tone]
    icn = ic if icn is None else icn
    body = (h_out(title, 16, 22, 700, INK, margin_bottom=2) if title else '') + div(content, font_size=14, line_height=20, color=INK)
    return div((icon(icn, 22, fg) if icn else '') + div(body, flex_grow=1), _id, 'Notice', _tag='tr', display='flex', align_items='flex-start', gap=10,
               background=bg, border_radius=14, padding='12px 14px', border=f'1px solid {BORDER}' if tone == 'info' else None)


def card(content, _id=None, bg=WHITE, _tag='tr', **style):
    base = dict(background=bg, border=f'1px solid {BORDER}', border_radius=14, box_shadow=SH_SM, box_sizing='border-box')
    base.update(style)
    return div(content, _id, 'Card', _tag=_tag, **base)


# ---------- screen frame ----------
KEYBOARD_H = 300


def keyboard_block():
    return div('Keyboard (about 300 dp)', display='flex', align_items='center', justify_content='center', height=KEYBOARD_H, background='#d9dde2',
               color='#5a6068', font_size=13, flex_shrink=0, _a={'data-keyboard': '1'})


def phone(header_html='', body_html='', footer_html='', overlay_html='', h=892, scroll=0, keyboard=False, bg=WHITE,
          body_pad='20px 16px 0', fade=False, inset=True, body_gap=16):
    foot = ''
    if footer_html:
        foot = (f'<div data-region="footer"{attrs(None, st(flex_shrink=0, padding=("12px 16px 12px" if keyboard else "12px 16px 64px"), background=WHITE, border_top=f"1px solid {BORDER}", box_shadow="0 -8px 24px rgba(22,19,31,0.08)", display="flex", flex_direction="column", gap=4))}>'
                + footer_html + '</div>')
    elif inset and not keyboard:
        foot = div('', height=48, flex_shrink=0, background=bg)
    fade_html = div('', position='absolute', left=0, right=0, bottom=0, height=28, background=f'linear-gradient(rgba(255,255,255,0), {bg})', pointer_events='none') if fade else ''
    inner = f'<div style="padding:{body_pad};display:flex;flex-direction:column;gap:{body_gap}px;transform:translateY(-{scroll}px)">{body_html}</div>'
    return (f'<div class="phone"{attrs(None, st(position="relative", overflow="hidden", width=412, height=h, box_sizing="border-box", background=bg, color=INK, font_family=BODY, display="flex", flex_direction="column"))}>'
            + header_html
            + f'<div data-region="body"{attrs(None, st(flex_grow=1, min_height=0, overflow="hidden", position="relative"))}>{inner}{fade_html}</div>'
            + foot + (keyboard_block() if keyboard else '')
            + (f'<div data-region="overlay"{attrs(None, st(position="absolute", left=0, top=0, width=412, height=h))}>{overlay_html}</div>' if overlay_html else '')
            + '</div>')


def scrim():
    return div('', position='absolute', left=0, top=0, width=412, height='100%', background='rgba(22,19,31,0.55)', _a={'data-scrim': '1'})


def dialog(title, body, buttons_html, title_id, body_id):
    box = div(h_out(title, 22, 28, 700, _id=title_id) + text(body, 16, 24, 400, INK, _id=body_id) + col(buttons_html, gap=8, margin_top=8),
              _sn='Dialog', _tag='tr', display='flex', flex_direction='column', gap=12, background=WHITE, border_radius=24, padding=24,
              box_shadow=SH_MD, box_sizing='border-box', width=364)
    return scrim() + div(box, position='absolute', left=0, top=0, width='100%', height='100%', display='flex', align_items='center', justify_content='center')


def modal(inner, box_id):
    box = div(inner, _id=box_id, _sn='Dialog', _tag='tr', display='flex', flex_direction='column', gap=12, background=WHITE, border_radius=24, padding=24,
              box_shadow=SH_MD, box_sizing='border-box', width=364)
    return scrim() + div(box, position='absolute', left=0, top=0, width='100%', height='100%', display='flex', align_items='center', justify_content='center')


def spinner(size=40, color=TEAL_DEEP, _id=None):
    return div('', _id, 'Spinner', width=size, height=size, box_sizing='border-box', border=f'4px solid {BORDER}', border_top_color=color,
               border_radius=999, flex_shrink=0)


def logo_img(size=56, radius=14, _id=None):
    return f'<img{attrs(_id, st(width=size, height=size, border_radius=radius, object_fit="cover", flex_shrink=0), {"src": LOGO, "alt": ""})}>'


def field_box(value='', unit='', state='default', _id=None, placeholder=''):
    border = {'default': f'1.5px solid {BORDER_STRONG}', 'focus': f'2px solid {TEAL_DEEP}', 'error': f'2px solid {DANGER}'}[state]
    inner = div(value, color=INK) if value else div(placeholder, color=MUTED, opacity='0.85')
    return div(inner + (div(unit, font_size=15, color=MUTED) if unit else ''), _sn='Field/Text', _id=_id, height=56, box_sizing='border-box', border=border,
               border_radius=8, padding='0 16px', display='flex', align_items='center', justify_content='space-between', font_size=17, background=WHITE,
               box_shadow='0 0 0 4px ' + TINT_TEAL if state == 'focus' else 'none', font_family=BODY)
