"""字幕文件：python3 tools/srt.py → out/<output>.srt
只用于配音驱动的时间轴（timeline.mode = "voice"）。和引擎的字幕层用同一份数据：timeline.json 里每个镜头的 phrases
（text 中文短句、en 英文译文、t0/t1 对齐好的起止秒，由 timeline.py 从 script/vo.json 生成）。
每个短句一条，时刻和引擎字幕层相同：短句开始时出现，结束后再留 0.25 秒（不超过下一句的开始），和成片里烧录的字幕逐条对得上。语言按 project.json 的 subtitles.langs（默认只有 zh），
双语时一条两行，按 langs 的顺序（例如 ["zh", "en"] 是中文在上、英文在下）。配音语言（短句有汉字算 zh，否则算 en）取 text，其他语言取短句的同名字段（en）。
短句缺译文时停下：先在 vo.json 补 "en"，重跑 timeline.py。"""
import json, re, sys
from common import ROOT, project, subtitles, voice_lang

SUB_TAIL = 0.25                                       # 和 web/core.js 的 SUB_TAIL 一致

cfg = project()
tl = json.load(open(ROOT / 'timeline.json', encoding='utf-8'))
if tl.get('mode', 'voice') != 'voice':
    sys.exit('字幕只用于配音驱动的时间轴（timeline.mode = "voice"）。')
LANGS = subtitles(cfg)['langs']


def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def line(p, lang):
    s = (p.get('text') if lang == voice_lang(p.get('text', '')) else p.get(lang)) or ''
    return re.sub(r'[，、；：,;:]+$', '', s.strip())


P = sorted(((sid, k, p) for sid, s in tl['scenes'].items() for k, p in enumerate(s.get('phrases') or [])
           if isinstance(p.get('t0'), (int, float)) and isinstance(p.get('t1'), (int, float)) and str(p.get('text', '')).strip()), key=lambda e: e[2]['t0'])
cues, miss = [], []
for i, (sid, k, p) in enumerate(P):
    for g in LANGS:
        if not line(p, g): miss.append(f'{sid} 第 {k} 句「{p.get("text", "")}」缺 {g}')
    cues.append((p['t0'], min(p['t1'] + SUB_TAIL, P[i + 1][2]['t0'] if i + 1 < len(P) else float('inf')), [line(p, g) for g in LANGS]))
if miss:
    sys.exit(f'subtitles.langs 是 {"+".join(LANGS)}，这些短句缺译文：' + '；'.join(miss[:8]) + (f' …共 {len(miss)} 处' if len(miss) > 8 else '') +
             '。在 script/vo.json 补（例如 "en": [按短句一句一条]），重跑 timeline.py。')
out = ROOT / 'out' / f"{cfg.get('output', 'video')}.srt"; out.parent.mkdir(exist_ok=True)
out.write_text('\n'.join(f"{j}\n{ts(a)} --> {ts(b)}\n" + '\n'.join(L) + '\n' for j, (a, b, L) in enumerate(cues, 1)), encoding='utf-8')
print(f'{len(cues)} 条字幕（{"+".join(LANGS)}）→', out)
