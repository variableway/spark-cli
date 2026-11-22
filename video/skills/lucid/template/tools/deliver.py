"""交付核对：python3 tools/deliver.py [--format 名字|all]（默认每个画幅都核对）
render.py --final 结束时自动运行。交付说明里核对硬约束，依据是这里打印的成片事实，不看工程里的文件：
有 SRT 文件不等于观众看得到字幕，配置里写了英文不等于画面上是英文。
读 out/ 下每个画幅的成片（正式档，没有就读草稿档并注明），打印：
  成片      路径、时长、画幅、帧率、文件大小
  音轨      有没有、时长、积分响度（LUFS）、真峰值
  配音      有 / 无，有时写后端、音色名、语速和 voice.why（读 tts.py full 记下的 audio/narration.json；讲解片没有配音时标出来）
  字幕      烧录：project.json 的 subtitles 和页面登记的 window.__SUBS（开没开、语言）；再在每个短句的中点渲染一帧，
            数画出了字幕的短句和画出的语言（引擎画字幕时 ctx.__role = 'subtitle'）。SRT：out/<output>.srt 有没有、几条、几种语言
  画面文字  每个镜头 0.3 / 0.6 / 0.9 处渲染，读引擎登记的字（经 txt() 等画在主画布上的字，不含字幕和装饰字），
            同一行的字合并成一段、按段去重（逐字动画中途单独飞着的一个字母不算），统计含中文、只有英文的各几段，并列出例子
  硬约束    自动加一条「配音、字幕和画面文字的语言和需求一致」，讲解片（genre 是 explainer）再加一条「讲解片有配音」；再抄需求里的硬约束：工程根目录 storyboard.md 里有标题含「硬约束」的一节时
            逐条抄原文（列表、编号或表格的每一行；表格第一列是原话，其余列附在后面）；没有这一节时保留上次在 交付核对.md 里手写的条目，
            第一次运行就在「硬约束」一节下面自己逐条写（需求里的每个名字、数字、事实各一条，用户原话照抄，写成「1. 原话」），再重跑一次
写出 out/交付核对.md：成片事实 + 硬约束逐条，每条后面留「做到了，第几秒 / 没做到，原因」给你填。
重跑时，已经填过的结果按原文对上的保留。成片早于工程最近的改动（web/、project.json、timeline.json、script/vo.json）时会提示：
页面上读到的字幕和文字是现在的工程，可能和成片不一致，重渲正式档后再核对。
不在统计范围内：画在离屏画布上再贴进来的字（例如 appWindow 里的截图）、图片和视频素材里本来就有的字。
"""
import sys, re, json, time, contextlib
from pathlib import Path
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
from common import ROOT, ffmpeg, project, timeline, formats, pop_format, out_name, probe, serve, open_page, uses_gpu, gpu_slot, subtitles

ARGV = sys.argv[1:]
_argv = sys.argv; sys.argv = ['layout.py']
from layout import INIT_JS, merge_lines, CLEAR_JS, GRAB_JS, HAS_TEXT       # 和版面审计同一套文字登记（带 deco、role）
sys.argv = _argv
FMTS = pop_format(ARGV) if '--format' in ARGV else list(formats())
CFG = project(); TL = timeline(); SUB = subtitles(CFG)
GENRE = CFG.get('genre') or ('explainer' if TL.get('mode') == 'voice' else 'promo')
OUT = ROOT / 'out'; DOC = OUT / '交付核对.md'
CJK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]'); LATIN = re.compile(r'[A-Za-z]')
TODO = '做到了，第 __ 秒 / 没做到，原因：__'
VF = None


# ---------------------------------------------------------------- 成片文件
def loudness(path):
    import subprocess
    r = subprocess.run([ffmpeg(), '-hide_banner', '-i', str(path), '-map', '0:a:0', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    try: return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r)[-1])
    except Exception: return None, None


def stale(video):
    """成片早于工程最近的改动时，返回最新改动的文件"""
    files = [p for p in (ROOT / 'web').rglob('*') if p.is_file()] + [ROOT / n for n in ('project.json', 'timeline.json', 'script/vo.json') if (ROOT / n).exists()]
    new = max(files, key=lambda p: p.stat().st_mtime, default=None)
    return new if new and new.stat().st_mtime > video.stat().st_mtime + 1 else None


def srt_facts():
    p = OUT / f"{CFG.get('output', 'video')}.srt"
    if not p.exists(): return None
    cues = [b for b in re.split(r'\n\s*\n', p.read_text(encoding='utf-8').strip()) if '-->' in b]
    body = [[l for l in b.splitlines()[2:] if l.strip()] for b in cues]
    zh = sum(1 for L in body if any(CJK.search(l) for l in L)); en = sum(1 for L in body if any(LATIN.search(l) and not CJK.search(l) for l in L))
    return dict(path=p, n=len(cues), zh=zh, en=en)


# ---------------------------------------------------------------- 页面：字幕和画面文字
def page_facts(pg, W, H):
    order = sorted(TL['scenes'].values(), key=lambda s: s['t0'])
    shots = [round(s['t0'] + f * s['dur'], 3) for s in order for f in (0.3, 0.6, 0.9)]
    phr = [((p['t0'] + p['t1']) / 2, p) for s in order for p in (s.get('phrases') or [])] if TL.get('mode') == 'voice' else []
    texts, subs, drawn, sub_langs = {}, None, 0, set()
    jobs = sorted([(t, 'shot', None) for t in shots] + [(t, 'phrase', p) for t, p in phr], key=lambda j: j[0])   # 时间只能向前（shader 背景）
    for t, kind, p in jobs:
        pg.evaluate(CLEAR_JS); pg.evaluate(f'render({min(t, TL["total"] - 1e-3)})'); fd = pg.evaluate(GRAB_JS)
        subs = subs or fd.get('subs')
        lines = [g for g in merge_lines(fd['txt']) if HAS_TEXT.search(g['s']) and g['a'] >= 0.5 and g['x1'] > 0 and g['x0'] < W and g['y1'] > 0 and g['y0'] < H]
        if kind == 'phrase':
            sl = [g['s'] for g in lines if g.get('role') == 'subtitle']
            if sl:
                drawn += 1
                for s_ in sl: sub_langs.add('zh' if CJK.search(s_) else 'en' if LATIN.search(s_) else '其他')
        else:
            for g in lines:
                if g.get('role') == 'subtitle' or g.get('deco'): continue
                if not CJK.search(g['s']) and len(re.findall(r'[A-Za-z0-9]', g['s'])) < 2: continue    # 逐字动画中途的单个字母
                texts.setdefault(re.sub(r'\s+', ' ', g['s'].strip()), round(t, 2))
    return dict(subs=subs, phrases=len(phr), drawn=drawn, sub_langs=sub_langs, texts=texts)


# ---------------------------------------------------------------- 硬约束
VOICE_ITEM = '讲解片有配音'
LANG_ITEM = '配音、字幕和画面文字的语言和需求一致'


def voice_facts():
    """配音事实：None = 没有配音；否则 {provider, voice, speed, why, sec}"""
    if TL.get('mode') != 'voice': return None
    wav = ROOT / 'audio' / 'narration.wav'
    if not wav.exists(): return None
    meta = {}
    jp = ROOT / 'audio' / 'narration.json'
    if jp.exists():
        try: meta = json.load(open(jp, encoding='utf-8'))
        except Exception: meta = {}
    v = CFG.get('voice') or {}
    if not meta:                                                     # 没有记录（旧配音）：按 project.json 推断
        prov = v.get('provider', 'auto')
        meta = {'provider': prov, 'voice': (v.get('edge') or {}).get('voice') if prov == 'edge' else ('录音 ' + (v.get('file') or {}).get('audio', '')) if prov == 'file' else v.get('voice_id') or '未记录', 'speed': v.get('speed'), 'why': v.get('why')}
    try: pi = probe(wav); meta['sec'] = pi.get('audio_sec') or pi.get('duration')
    except Exception: meta['sec'] = None
    return meta


def voice_line(vf):
    if vf is None:
        return '- **配音**：无' + ('（讲解片默认有配音；用户说了不要配音，就在交付说明里写明）' if GENRE == 'explainer' else '')
    sp = f"，语速 {vf['speed']}" if vf.get('speed') not in (None, '') else ''
    default = vf.get('voice') in ('Chinese (Mandarin)_Gentleman', 'English_Trustworthy_Man', 'zh-CN-YunxiNeural', 'en-US-GuyNeural')
    return (f"- **配音**：有（{vf.get('voice')}，{vf.get('provider')}{sp}" + (f"，{vf['sec']:.1f} 秒" if vf.get('sec') else '') + '）'
            + (f"。换音色的理由：{vf['why']}" if vf.get('why') else '。默认音色' if default else '。换了默认音色：理由写进交付说明（或写进 project.json 的 voice.why）'))


def constraints():
    """storyboard.md 里标题含「硬约束」的那一节：[(原文, 附注)]；没有这一节返回 None"""
    p = ROOT / 'storyboard.md'
    if not p.exists(): return None
    L = p.read_text(encoding='utf-8').splitlines()
    i = next((k for k, l in enumerate(L) if re.match(r'^#+\s.*硬约束', l)), None)
    if i is None: return None
    lv = len(L[i]) - len(L[i].lstrip('#')); items = []
    for k in range(i + 1, len(L)):
        l = L[k].strip()
        m = re.match(r'^(#+)\s', l)
        if m and len(m.group(1)) <= lv: break
        if l.startswith('|'):
            cells = [c.strip() for c in l.strip('|').split('|')]
            nxt = L[k + 1].strip() if k + 1 < len(L) else ''
            if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c) or re.match(r'^\|\s*:?-{2,}', nxt): continue   # 分隔行、表头
            if cells and cells[0]: items.append((cells[0], '；'.join(c for c in cells[1:] if c)))
            continue
        m = re.match(r'^(?:[-*+]|\d+[.、)）])\s*(.+)$', l)
        if m: items.append((m.group(1).strip(), ''))
    return items


def old_results():
    """上一次 交付核对.md 「硬约束」一节：({原文: 已填的结果}, [原文，按顺序])"""
    if not DOC.exists(): return {}, []
    out, order, cur, on = {}, [], None, False
    for l in DOC.read_text(encoding='utf-8').splitlines():
        if l.startswith('## '): on = l.strip() == '## 硬约束'; continue
        if not on: continue
        m = re.match(r'^\d+\.\s(.+)$', l)
        if m: cur = m.group(1).strip(); order.append(cur); continue
        m = re.match(r'^\s+- 结果：(.*)$', l)
        if m and cur and m.group(1).strip() != TODO: out[cur] = m.group(1).strip()
    return out, order


# ---------------------------------------------------------------- 主流程
def fmt_facts(fmt, url, p):
    W, H = formats()[fmt]
    v = OUT / out_name(fmt); draft = False
    if not v.exists():
        v = OUT / out_name(fmt, '_draft'); draft = True
    if not v.exists(): return dict(fmt=fmt, missing=True)
    info = probe(v); lu, tp = loudness(v) if info['audio'] else (None, None)
    b, pg, errs = open_page(p, url, fmt, init_script=INIT_JS); pg.evaluate('window.__MB_OFF = true; window.__REC = true')
    pf = page_facts(pg, W, H); b.close()
    return dict(fmt=fmt, video=v, draft=draft, info=info, lufs=lu, peak=tp, stale=stale(v), **pf)


def lines_for(f, srt):
    if f.get('missing'): return [f"- **{f['fmt']}**：out/ 里没有成片（{out_name(f['fmt'])}），先运行 python3 tools/render.py --final"]
    i = f['info']; L = []
    rel = f['video'].relative_to(ROOT)
    L.append(f"- **成片**（{f['fmt']}）：{rel}" + ('（草稿档：没有正式档）' if f['draft'] else '') +
             f"　{i['duration']:.2f} 秒　{i['width']}×{i['height']}　{i['fps']:g} 帧/秒　{i['mb']:.1f} MB")
    L_voice = voice_line(VF)
    if i['audio']:
        L.append(f"- **音轨**：有，{i['audio_sec']:.1f} 秒" + (f"，积分响度 {f['lufs']:.1f} LUFS，真峰值 {f['peak']:.1f} dBFS" if f['lufs'] is not None else '，响度没读出来'))
    else: L.append('- **音轨**：没有（成片无声）')
    L.append(L_voice if i['audio'] or VF is None else L_voice + '；但成片没有音轨')
    S = f['subs'] or {}
    srt_s = (f"另有 SRT（{srt['path'].relative_to(ROOT)}，{srt['n']} 条，含中文 {srt['zh']} 条、含英文 {srt['en']} 条）" if srt else '没有 SRT 文件')
    if SUB['burn'] and S.get('on'):
        langs = '+'.join(S.get('langs') or SUB['langs'])
        seen = '+'.join(x for x in ('zh', 'en', '其他') if x in f['sub_langs']) or '没有'
        L.append(f"- **字幕**：烧录 {langs}，{srt_s}。抽查 {f['phrases']} 个短句的中点，{f['drawn']} 个画出了字幕，画出的语言 {seen}"
                 + ('' if f['drawn'] == f['phrases'] and f['phrases'] else '（有短句没画出字幕：看这几处静帧）'))
    elif SUB['burn']:
        L.append(f"- **字幕**：project.json 开了 subtitles.burn，但页面没有登记字幕层开着（window.__SUBS.on），成片里多半没有字幕。{srt_s}")
    else:
        L.append(f"- **字幕**：没有烧录（project.json 没开 subtitles.burn），{srt_s}")
    T = f['texts']; zh = [s for s in T if CJK.search(s)]; en = [s for s in T if LATIN.search(s) and not CJK.search(s)]
    ex = lambda xs: '、'.join(f'「{s[:16]}」' for s in xs[:5]) + (' …' if len(xs) > 5 else '')
    L.append(f"- **画面文字**：{len(T)} 段（每个镜头 0.3/0.6/0.9 处，不含字幕和装饰字），含中文 {len(zh)} 段，只有英文 {len(en)} 段，其他（数字、符号）{len(T) - len(zh) - len(en)} 段"
             + (f"。只有英文的：{ex(en)}" if en else '') + (f"。含中文的：{ex(zh)}" if zh else ''))
    if f['stale']:
        L.append(f"- ⚠️ 成片早于工程最近的改动（{f['stale'].relative_to(ROOT)}）：上面的字幕和画面文字读的是现在的工程，可能和成片不一致，重渲正式档后再核对")
    return L


def main():
    global VF
    t0 = time.time(); srt = srt_facts(); VF = voice_facts()
    lease = gpu_slot() if uses_gpu(CFG) else contextlib.nullcontext()
    from playwright.sync_api import sync_playwright
    with lease, sync_playwright() as p, serve() as url:
        facts = [fmt_facts(fmt, url, p) for fmt in FMTS]
    items = constraints(); old, old_order = old_results(); from_sb = items is not None
    if items is None: items = [(x, '') for x in old_order if x not in (VOICE_ITEM, LANG_ITEM)]          # 没有 storyboard.md：保留上次手写的条目
    items = [x for x in items if x[0] not in (VOICE_ITEM, LANG_ITEM)]
    T = {s for f in facts if not f.get('missing') for s in f['texts']}
    zh = sum(1 for s in T if CJK.search(s)); en = sum(1 for s in T if LATIN.search(s) and not CJK.search(s))
    fixed = [(LANG_ITEM, f'依据：成片事实的「画面文字」「字幕」「配音」三行（现在画面文字含中文 {zh} 段、只有英文 {en} 段' + ('' if VF is None else f"，配音 {VF.get('voice')}") + '）')]
    if GENRE == 'explainer':
        fixed = [(VOICE_ITEM, '依据：成片事实的「配音」一行' + ('（现在是：无）' if VF is None else f"（现在是：有，{VF.get('voice')}）"))] + fixed
    items = fixed + items
    D = ['# 交付核对', '', f'> deliver.py 生成（{time.strftime("%Y-%m-%d %H:%M")}）。成片事实从成片文件和页面读出；硬约束逐条填「做到了，第几秒」或「没做到，原因」，依据只用成片事实和成片的静帧。', '',
         '## 成片事实', '']
    for f in facts: D += lines_for(f, srt)
    D += ['', '## 硬约束', '']
    for k, (txt, note) in enumerate(items, 1):
        D += [f'{k}. {txt}'] + ([f'   - 方案：{note}'] if note else []) + [f'   - 结果：{old.get(txt, TODO)}']
    if not from_sb and len(items) <= len(fixed):
        D += ['', '（在这里接着写需求里的硬约束：把需求里的名字、数字、事实逐条写上，每条一行，用户原话照抄，写成「编号. 原话」，下面一行「   - 结果：」。重跑 deliver.py 会保留这些条目和已填的结果。）']
    OUT.mkdir(exist_ok=True); DOC.write_text('\n'.join(D) + '\n', encoding='utf-8')
    print('[交付核对] 成片事实：')
    for f in facts:
        for l in lines_for(f, srt): print('  ' + l.replace('**', ''))
    n_todo = sum(1 for txt, _ in items if txt not in old)
    print(f'  硬约束 {len(items)} 条' + (f'，{n_todo} 条待填' if items else '') + ('' if from_sb or len(items) > len(fixed) else '（需求里的硬约束还没写：把需求里的名字、数字、事实逐条写进 交付核对.md 的「硬约束」一节，再重跑）') + f' → {DOC}（{time.time() - t0:.0f} 秒）')


if __name__ == '__main__':
    main()
