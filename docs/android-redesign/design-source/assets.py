"""Write the vector assets and the 512 px store icon. Run: uv run --no-project --with playwright python assets.py"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from screens_c import MARK, MONO, gradient, svg_fg, svg_bg, svg_mono, svg_splash  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

import config  # noqa: E402

DEST = config.RETURN / 'assets'
DEST.mkdir(parents=True, exist_ok=True)
(DEST / 'ic_launcher_foreground.svg').write_text(svg_fg(), encoding='utf-8')
(DEST / 'ic_launcher_background.svg').write_text(svg_bg(), encoding='utf-8')
(DEST / 'ic_launcher_monochrome.svg').write_text(svg_mono(), encoding='utf-8')
(DEST / 'splash_icon.svg').write_text(svg_splash(), encoding='utf-8')
(DEST / 'logo_mark.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="22 20 64 70" width="256" height="280">{MARK}</svg>\n', encoding='utf-8')
(DEST / 'logo_mark_mono.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="22 20 64 70" width="256" height="280" fill="#16131f">{MONO}</svg>\n', encoding='utf-8')
html = (f'<body style="margin:0"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108" width="512" height="512"><defs>{gradient("g")}</defs>'
        f'<rect width="108" height="108" fill="url(#g)"/>{MARK}</svg></body>')
config.OUT.mkdir(parents=True, exist_ok=True)
f = config.OUT / 'icon512.html'
f.write_text(html, encoding='utf-8')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=config.chrome_path()) if config.chrome_path() else p.chromium.launch()
    pg = b.new_page(viewport={'width': 512, 'height': 512})
    pg.goto(f.as_uri())
    pg.screenshot(path=str(DEST / 'ic_launcher_512.png'))
    b.close()
print('ok', sorted(x.name for x in DEST.iterdir()))
