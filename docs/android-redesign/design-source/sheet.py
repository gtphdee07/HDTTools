import sys, pathlib
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config  # noqa: E402

OUT = config.OUT
names = sys.argv[2:]
tag = sys.argv[1]
imgs = ''.join(f'<div style="width:330px;font:12px sans-serif"><div>{n}</div><img src="{(OUT/"png"/(n+".png")).as_uri()}" style="width:330px;border:1px solid #ccc"></div>' for n in names)
html = f'<body style="margin:8px;background:#eee"><div style="display:flex;flex-wrap:wrap;gap:8px;width:1360px">{imgs}</div></body>'
f = OUT / f'sheet_{tag}.html'
f.write_text(html, encoding='utf-8')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=config.chrome_path()) if config.chrome_path() else p.chromium.launch()
    pg = b.new_page(viewport={'width': 1380, 'height': 800})
    pg.goto(f.as_uri()); pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / f'sheet_{tag}.png'), full_page=True)
    b.close()
