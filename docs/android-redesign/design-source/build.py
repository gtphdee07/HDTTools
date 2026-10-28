"""Render every state: standalone HTML, annotated PNG at 2x, measurement JSON, and a .dc.html board for the canvas.

Run from this folder:  uv run --no-project --with playwright python build.py [only-substring]
"""
import json
import pathlib
import sys

GEN = pathlib.Path(__file__).parent
sys.path.insert(0, str(GEN))
import config  # noqa: E402
import screens_a  # noqa: E402,F401
import screens_b  # noqa: E402,F401
import screens_c  # noqa: E402,F401
from screens_a import STATES  # noqa: E402
from lib import LOGO  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = config.OUT
CHROME = config.chrome_path()
LOGO_FILE = config.LOGO_FILE
FONTS = 'https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=DM+Sans:wght@400;500;700&display=swap'

HEAD_CSS = "body{margin:0}button,input{font-family:'DM Sans',system-ui,sans-serif}"

ANNOTATE_JS = r"""
() => {
  const phone = document.querySelector('.phone');
  const pr = phone.getBoundingClientRect();
  const body = phone.querySelector('[data-region="body"]');
  const br = body ? body.getBoundingClientRect() : null;
  const out = [];
  const ovl = phone.querySelector('[data-region="overlay"]');
  const modal = ovl && ovl.querySelector('[data-scrim]') ? ovl : null;
  let n = 0;
  const layer = document.createElement('div');
  layer.style.cssText = 'position:absolute;left:0;top:0;width:' + pr.width + 'px;height:' + pr.height + 'px;pointer-events:none;z-index:9999';
  phone.appendChild(layer);
  document.querySelectorAll('[data-id]').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    if (modal && !modal.contains(el)) return;
    const inBody = el.closest('[data-region="body"]');
    if (inBody && br) {
      const cy = r.top + r.height / 2;
      if (cy < br.top || cy > br.bottom) return;
    }
    if (r.right < pr.left || r.left > pr.right || r.bottom < pr.top || r.top > pr.bottom) return;
    n += 1;
    const x = r.left - pr.left, y = r.top - pr.top;
    const reg = el.closest('[data-region]');
    out.push({n, id: el.dataset.id, x: +x.toFixed(1), y: +y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1),
              region: reg ? reg.dataset.region : 'body', style: el.dataset.style || null,
              ff: getComputedStyle(el).fontFamily.split(',')[0].replace(/['"]/g, ''), fs: getComputedStyle(el).fontSize, fw: getComputedStyle(el).fontWeight,
              lh: getComputedStyle(el).lineHeight, ls: getComputedStyle(el).letterSpacing, color: getComputedStyle(el).color, bg: getComputedStyle(el).backgroundColor});
    const box = document.createElement('div');
    box.style.cssText = 'position:absolute;left:' + x + 'px;top:' + y + 'px;width:' + r.width + 'px;height:' + r.height + 'px;outline:1px dashed rgba(91,37,184,0.65);outline-offset:-1px';
    layer.appendChild(box);
    const tr = el.dataset.tag === 'tr' || el.dataset.tag === 'br';
    const tag = document.createElement('div');
    tag.textContent = n;
    const tx = Math.min(Math.max(tr ? x + r.width - 12 : x - 7, 1), pr.width - 20);
    const ty = Math.min(Math.max(el.dataset.tag === 'br' ? y + r.height - 11 : y - 7, 1), pr.height - 20);
    tag.style.cssText = 'position:absolute;left:' + tx + 'px;top:' + ty + 'px;min-width:18px;height:18px;padding:0 3px;box-sizing:border-box;border-radius:9px;background:#16131f;color:#fff;font:700 11px/18px DM Sans,sans-serif;text-align:center;border:1px solid #fff';
    layer.appendChild(tag);
  });
  return out;
}
"""

SCROLL_JS = r"""
(id) => {
  const body = document.querySelector('[data-region="body"]');
  const inner = body.firstElementChild;
  const t = document.querySelector('[data-id="' + id + '"]');
  const off = t.getBoundingClientRect().top - inner.getBoundingClientRect().top;
  const max = Math.max(0, inner.offsetHeight - body.clientHeight);
  return Math.round(Math.min(Math.max(0, off - 40), max));
}
"""


def standalone(html, title):
    html = html.replace(LOGO, LOGO_FILE)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><link rel="stylesheet" href="{FONTS}">'
            f'<style>{HEAD_CSS}</style></head><body>{html}</body></html>')


def dc_board(html, title, w, h):
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<title>{title}</title>\n<script src="./support.js"></script>\n</head>\n<body>\n<x-dc>\n<helmet>\n'
            f'<link rel="stylesheet" href="{FONTS}">\n<style>\n{HEAD_CSS}\n</style>\n</helmet>\n{html}\n</x-dc>\n'
            '<script type="text/x-dc" data-dc-script data-props=\'{"$preview":{"width":' + str(w) + ',"height":' + str(h) + '}}\'>\n'
            'class Component extends DCLogic {\nrenderVals() {\nreturn {};\n}\n}\n</script>\n</body>\n</html>\n')


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ''
    for d in ('html', 'png', 'meta', 'boards'):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    legends = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True) if CHROME else p.chromium.launch(headless=True)
        for s in STATES:
            name = f"{s['screen']}__{s['name']}"
            if only and only not in name:
                continue
            w, h = s.get('w', 412), s['h']
            ctx = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2)
            page = ctx.new_page()
            scroll = 0
            if s['scroll_to']:
                f0 = OUT / 'html' / f'{name}.pass0.html'
                f0.write_text(standalone(s['build'](0), name), encoding='utf-8')
                page.goto(f0.as_uri())
                page.evaluate('document.fonts.ready')
                scroll = page.evaluate(SCROLL_JS, s['scroll_to'])
                f0.unlink()
            html = s['build'](scroll)
            f = OUT / 'html' / f'{name}.html'
            f.write_text(standalone(html, name), encoding='utf-8')
            page.goto(f.as_uri())
            page.evaluate('document.fonts.ready')
            page.wait_for_timeout(250)
            ok = page.evaluate("[...document.fonts].some(f => f.family.includes('Outfit') && f.status === 'loaded') && [...document.fonts].some(f => f.family.includes('DM Sans') && f.status === 'loaded')")
            if not ok:
                print('WARN fonts not loaded for', name)
            (OUT / 'boards' / f'{name}.dc.html').write_text(dc_board(html, name.replace('__', ': '), w, h), encoding='utf-8')
            meta = page.evaluate(ANNOTATE_JS)
            page.locator('.phone').screenshot(path=str(OUT / 'png' / f'{name}.png'))
            (OUT / 'meta' / f'{name}.json').write_text(json.dumps({'screen': s['screen'], 'state': s['name'], 'w': w, 'h': h, 'scroll': scroll, 'elements': meta}, indent=1), encoding='utf-8')
            legends[name] = [{'n': m['n'], 'id': m['id']} for m in meta]
            print(name, 'scroll', scroll, 'tags', len(meta))
            ctx.close()
        browser.close()
    if not only:
        (OUT / 'legends.json').write_text(json.dumps(legends, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
