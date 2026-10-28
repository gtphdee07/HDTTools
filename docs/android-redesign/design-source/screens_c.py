"""Splash, app icon and the components sheet."""
from lib import *
from screens_a import add, STATES

SKY_TOP = '#7b3fe4'
SKY_BOTTOM = '#ff7a1a'

# Simplified vector mark: mountain, camper, ground line. 108 x 108 adaptive-icon canvas, safe zone r=33 around (54,54).
MARK = ('<polygon points="54,24 78,64 30,64" fill="#576775"/>'
        '<polygon points="54,24 61,36 54,33 47,36" fill="#ffffff"/>'
        '<polygon points="26,66 40,44 56,66" fill="#3f6b35"/>'
        '<rect x="33" y="58" width="42" height="23" rx="7" fill="#ffffff"/>'
        '<rect x="33" y="72" width="42" height="6" fill="#ffb627"/>'
        '<rect x="38" y="62" width="9" height="7" rx="2" fill="#2f9bef"/>'
        '<rect x="50" y="62" width="9" height="7" rx="2" fill="#2f9bef"/>'
        '<rect x="64" y="62" width="7" height="14" rx="2" fill="#ff7a1a"/>'
        '<circle cx="47" cy="82" r="4.6" fill="#576775"/><circle cx="47" cy="82" r="1.7" fill="#ffffff"/>'
        '<rect x="27" y="83" width="54" height="3" rx="1.5" fill="#3f6b35"/>')

MONO = ('<path fill-rule="evenodd" d="M54 24 78 64H30zM33 65a7 7 0 0 1 7-7h28a7 7 0 0 1 7 7v10a7 7 0 0 1-7 7H40a7 7 0 0 1-7-7zM38 62h9v7h-9zM50 62h9v7h-9zM64 62h7v14h-7z"/>'
        '<rect x="27" y="85" width="54" height="3" rx="1.5"/>')


def gradient(gid):
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SKY_TOP}"/><stop offset="1" stop-color="{SKY_BOTTOM}"/></linearGradient>'


def svg_fg():
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108" width="108" height="108">{MARK}</svg>\n'


def svg_bg():
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108" width="108" height="108"><defs>{gradient("g")}</defs><rect width="108" height="108" fill="url(#g)"/></svg>\n'


def svg_mono():
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108" width="108" height="108" fill="#000000">{MONO}</svg>\n'


def svg_splash():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 288 288" width="288" height="288"><g transform="translate(54 54) scale(1.667)">{MARK}</g></svg>\n')


def icon_svg(size, mask, gid, mono=False):
    radius = {'circle': '50%', 'squircle': '34%', 'rounded': '22%', 'square': '0'}[mask]
    if mono:
        inner = f'<rect width="108" height="108" fill="#e7e0ff"/><g fill="{PURPLE_DEEP}">{MONO}</g>'
    else:
        inner = f'<defs>{gradient(gid)}</defs><rect width="108" height="108" fill="url(#{gid})"/>{MARK}'
    return (f'<svg aria-hidden="true" viewBox="0 0 108 108" style="width:{size}px;height:{size}px;border-radius:{radius};box-shadow:{SH_MD};flex-shrink:0;overflow:hidden">{inner}</svg>')


def splash(sc):
    body = div(
        div(f'<svg aria-hidden="true" viewBox="0 0 108 108" style="width:200px;height:200px;border-radius:50%;overflow:hidden;box-shadow:{SH_MD}"><defs>{gradient("sg")}</defs><rect width="108" height="108" fill="url(#sg)"/>{MARK}</svg>',
            _id='splash.icon', _sn='SplashIcon')
        , _id='splash.background', _sn='SplashBackground', position='absolute', left=0, top=0, width=412, height=892, background=TEAL, display='flex', align_items='center', justify_content='center')
    brand = div(h_out('RigCheck', 28, 32, 800, INK, letter_spacing='-0.01em') + text('Weight safety, before you roll', 14, 20, 400, INK), position='absolute', left=0, right=0, bottom=96, display='flex', flex_direction='column', align_items='center', gap=2, _id='splash.branding')
    return f'<div class="phone" style="position:relative;overflow:hidden;width:412px;height:892px;background:{TEAL};font-family:{BODY}">{body}{brand}</div>'


add('splash', 'default', splash)


def app_icon(sc):
    def tile(label, content):
        return col(content + text(label, 13, 18, 500, MUTED, text_align='center'), gap=8, align_items='center')
    row1 = row(tile('Circle mask', icon_svg(160, 'circle', 'a1')) + tile('Squircle mask', icon_svg(160, 'squircle', 'a2')) + tile('Rounded square', icon_svg(160, 'rounded', 'a3'))
               + tile('Themed (monochrome)', icon_svg(160, 'circle', 'a4', mono=True)), gap=28, align='flex-start', _id='app_icon.adaptive')
    row2 = row(tile('Store listing, 512 px square', icon_svg(180, 'square', 'a5')) + col(
        h_out('Layers', 18, 22, 700) + text('Foreground: the mark, drawn inside the 66 dp safe zone of a 108 dp canvas.', 14, 20, 400, MUTED)
        + text('Background: a sky gradient, purple to orange, from the brand palette.', 14, 20, 400, MUTED)
        + text('Monochrome: one-colour silhouette for themed icons.', 14, 20, 400, MUTED), gap=6, max_width=420), gap=32, align='center', _id='app_icon.layers')
    return div(h_out('App icon', 26, 30, 800) + row1 + row2, display='flex', flex_direction='column', gap=28, padding=32, background=WHITE, width=900, height=620, box_sizing='border-box', _a={'class': 'phone'})


STATES.append(dict(screen='app_icon', name='launcher', build=app_icon, scroll_to=None, h=620, w=900))
