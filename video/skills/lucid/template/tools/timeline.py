"""时间轴：python3 tools/timeline.py [--estimate]
按 project.json 的 timeline.mode 生成 timeline.json，并同步 web/project.js、web/timeline.js、index.html。每次改了 project.json 或新增镜头文件都要重跑。

  beats   节拍网格（无配音的宣传片、showreel、音乐卡点片）
          "timeline": {"mode": "beats", "bpm": 128, "offset": 0, "shots": [{"id": "S01", "beats": 8, "label": "钩子"}, ...]}
          offset：用户歌曲里第一拍的时刻（秒），合成配乐时为 0。镜头里用 b(n) 取第 n 拍的时刻。
  manual  手写时长（不卡拍的片子、UI 循环、按参考片对时）
          "timeline": {"mode": "manual", "bpm": 120, "shots": [{"id": "S01", "dur": 2.4}, ...]}   也可以写 {"id", "t0", "t1"}
  voice   配音驱动（讲解片）：转给 tools/build_timeline.py，读 script/vo.json 和 audio/narration.wav（tools/tts.py full 生成）；
          短句带 text 和 en（vo.json 写了英文才有），字幕层和 srt.py 读它们；subtitles.langs 含 en 而短句缺 en 时停下并列出；
          还没有配音时加 --estimate 按音节估时。镜头时长由配音决定，shots 只写镜头属性（可省略）：
          "timeline": {"mode": "voice", "bpm": 80, "shots": [{"id": "S04", "motion": "可以震"}]}
  motion  每个镜头的运动标签，三种模式都一样：「稳」（默认）或「可以震」（允许震动、抖动等有意设计的剧烈运动）。
  总时长：默认是最后一个镜头的结束时刻；"total": 15.0 直接指定（镜头不够长时最后一段留给落版），"tail": 0.5 在末尾补一段。
          例：128 BPM 的 32 拍是 15.000 秒，30 拍是 14.0625 秒；需求要求整数秒时用 total 补齐，不要改 BPM 凑数。
配色门禁：project.json 的 theme.colors 必须有 bg（背景）、ink（主文字）、acc（强调色），缺一项就停下。模板和引擎不给配色默认值：
          色调和背景要按这支片子的题材和观众定，不能照用一个默认的深色底。字体缺省时回落到系统字体，不拦。
"""
import sys, subprocess
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
from common import ROOT, project, subtitles
from tl_io import write_all

cfg = project()
_cols = (cfg.get('theme') or {}).get('colors') or {}
_miss = [k for k in ('bg', 'ink', 'acc') if not _cols.get(k)]
if _miss:
    sys.exit(f'project.json 的 theme.colors 缺 {"、".join(_miss)}，没有同步时间轴。\n'
             '按题材和观众定色调和背景，写进 theme.colors：bg 背景、ink 主文字、acc 强调色（其余颜色按需要加），再运行 timeline.py。')
T = cfg.get('timeline') or {'mode': 'voice'}
mode = T.get('mode', 'voice')
if mode == 'voice':
    sys.exit(subprocess.call([sys.executable, str(ROOT / 'tools' / 'build_timeline.py')] + sys.argv[1:]))
if subtitles(cfg)['burn']:
    sys.exit('project.json 的 subtitles.burn 只用于配音驱动的时间轴（timeline.mode = "voice"）：字幕层按配音短句画。'
             '没有配音的片子，要让观众读的字直接排进画面。')

FPS = cfg.get('fps', 60)
BPM = T.get('bpm', 120); BEAT = 60 / BPM; BAR = 4 * BEAT; OFF = T.get('offset', 0.0)
scenes = {}; t = OFF if mode == 'beats' else 0.0; bt = 0
for s in T['shots']:
    if mode == 'beats':
        d = s['beats'] * BEAT; t0 = t
    elif 't0' in s:
        t0 = s['t0']; d = s['t1'] - s['t0']
    else:
        t0 = t; d = s['dur']
    sc = {'id': s['id'], 'label': s.get('label', ''), 'motion': '可以震' if s.get('motion') == '可以震' else '稳', 'chapter': s.get('chapter', s['id']),
          't0': round(t0, 6), 't1': round(t0 + d, 6), 'dur': round(d, 6), 'v0': round(t0, 6), 'v1': round(t0 + d, 6),
          'phrases': [{'text': s.get('label', ''), 't0': round(t0, 6), 't1': round(t0 + d, 6)}]}
    if mode == 'beats':
        sc.update({'b0': bt, 'b1': bt + s['beats'], 'beats': s['beats']}); bt += s['beats']
    scenes[s['id']] = sc; t = t0 + d
TOTAL = round(T.get('total', max(s['t1'] for s in scenes.values()) + T.get('tail', 0.0)), 6)
chs = {}
for s in scenes.values():
    c = chs.setdefault(s['chapter'], {'id': s['chapter'], 'scenes': [], 't0': s['t0'], 't1': s['t1']})
    c['scenes'].append(s['id']); c['t1'] = s['t1']
tl = {'mode': mode, 'fps': FPS, 'total': TOTAL, 'bpm': BPM, 'beat': BEAT, 'bar': BAR, 'offset': OFF, 'estimate': False,
      'chapters': list(chs.values()), 'scenes': scenes}
msg = write_all(tl, cfg)
print(f'{mode} 时间轴：{TOTAL:.3f} 秒，{len(scenes)} 个镜头，{BPM} BPM（一拍 {BEAT:.4f} 秒，一小节 {BAR:.3f} 秒）')
for s in scenes.values():
    extra = f"  拍 {s['b0']:>3}–{s['b1']:<3}" if 'b0' in s else ''
    print(f"  {s['id']:6s} {s['t0']:7.3f}–{s['t1']:7.3f}  ({s['dur']:.2f}s){extra}  {s['label']}")
print(msg)
