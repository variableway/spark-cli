"""从页面导出音效事件表 → audio/events.json（镜头代码里用 EV(t, type, opts) 登记的全部事件，按时间排序）。
须在 build_timeline 之后、synth 之前运行。
只导出页面加载时（镜头文件顶层）登记的事件，导出时不会调用 render(t)。写在绘制函数里的 EV() 每帧都会登记，导出时拿不到，所以导出后会再调用几次 render(t)：事件数变多就打印警告。
"""
import json
from collections import Counter
from playwright.sync_api import sync_playwright
from common import ROOT, serve, open_page

with sync_playwright() as p, serve() as url:
    b, pg, errs = open_page(p, url)
    ev = pg.evaluate('EVENTS.slice().sort((a,b)=>a.t-b.t)')
    total = pg.evaluate('TL.total'); n0 = pg.evaluate('EVENTS.length')
    for f in (0.31, 0.62, 0.93):
        try: pg.evaluate(f'render({total * f})')
        except Exception as e: errs.append('render 抛错：' + str(e)[:200]); break
    grown = pg.evaluate(f'EVENTS.slice({n0}).map(e => e.type)')
    b.close()
if errs: print('页面错误：', errs[:4])
if grown:
    print(f'⚠️ 调用 render(t) 之后事件数从 {n0} 变成 {n0 + len(grown)}（多出 {dict(Counter(grown))}）：有 EV() 写在了绘制函数里。它每帧都会登记，导出时拿不到，这些音效会丢。把 EV(...) 移到镜头文件顶层（只执行一次），时刻用和画面相同的表达式算。')
json.dump(ev, open(ROOT / 'audio' / 'events.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(ev), '个音效事件', dict(Counter(e['type'] for e in ev)))
