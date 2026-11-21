"""渲染：逐帧 render(t) → 直接读画布编码 JPEG → 管道给 ffmpeg，分段并行，最后拼接并混入 audio/mix_final.wav。渲完自动体检，终端打印摘要。
  python3 tools/render.py                  草稿档（默认）：半尺寸、最高 30 帧/秒、不开运动模糊、CRF 28 快速编码 → out/<output>_draft.mp4
  python3 tools/render.py --final          正式档：原尺寸、project.json 的帧率、运动模糊、CRF 18 → out/<output>.mp4（交付用这个）
  python3 tools/render.py 起始秒 结束秒     只渲一段（抽查转场）→ out/part_<起>-<止>[_draft].mp4，可与 --final 合用；只渲一段时不跑体检
  选项：--format 名字|all 画幅   -j N 进程数（默认 4；开 shader 时 3）   --fresh 不复用已渲好的分段
        --master 正式档额外出 CRF 14 母版（和 --final 一起用）   --share 正式档额外出 6 Mbps 小文件（和 --final 一起用）
        --no-preflight 跳过页面预检和版面检查（合同预检照样跑）   --no-checkup 渲完不跑体检   --no-sync 不做渲染前同步
渲染前同步（自动）：project.json、vo.json、配音比时间轴新，或有新的 shots_*.js 没登记时先跑 timeline.py；
  页面代码、时间轴变了时先跑 dump_events.py，音效事件、时间轴或配乐设置变了时再跑 audio/synth.py。改完代码直接渲，不用手动跑这三步。
迭代用草稿档，确认没问题后出一次正式档。两档的分段各自复用，互不影响。
收尾打印成片信息：路径、时长、画幅、帧率、有没有音轨（和音轨时长）、文件大小（用自带的 ffmpeg 读，不需要 ffprobe）。
正式档最后运行 tools/deliver.py：打印成片事实（音轨响度、字幕是否烧录和语言、画面文字的语言），把硬约束清单抄进 out/交付核对.md 待填。

渲染前依次检查，任何一步有问题都直接停下，不进入渲染：
  1 合同预检（tools/lint.py）：镜头文件里的 Math.exp(-(t - …))、setTransform(1, 0, 0, 1, 0, 0)、Math.random()、Date.now()、
    绘制函数里的 EV() 等写法，打印文件:行号和改法。确实需要的行在行尾写 // lint-ok: 原因。
  2 页面预检：每 0.25 秒调用一次 render(t)（不截图），收集 JS 报错、console.error，并检查画布调用（moveTo、lineTo、arc、fillRect、
    drawImage、translate、scale 等）里有没有 NaN 或无穷大的参数。画布遇到 NaN 不报错，只是这一笔不画，症状是「某个东西莫名其妙不见了」。
  3 版面（tools/layout.py，只在渲整片时）：字出框、字压字、标注没落到目标（❌）。每条带镜头文件的行号。
    字太小、⚠️ 和可选提示不拦渲染，结果直接交给渲染后的体检，不重复跑。
渲完的体检摘要：「硬伤 N 条（❌ a、⚠️ b）；可选提示 M 条见报告」，下面只列硬伤。

按镜头增量渲染（只重渲改过的镜头）：
  分段按镜头切：每个镜头的起点是分段边界，长镜头再按约 4 秒切开，放进一个队列，N 个进程一段接一段地取（每个进程只开一次浏览器）。
  每段有一个指纹，指纹没变的段直接复用上次的结果。指纹 =
    公共部分：web/ 下的引擎和模块（core.js、main.js、modules/ 等）、共用的镜头文件（shots_00_* 和不定义 SHOT 的 shots_*.js）、
              project.json、timeline.json、字体和图片清单（文件名、大小、修改时间）、页面上登记的 SHAKES / FLASH / CUTS / FAST，
              以及档位参数（帧率、尺寸、运动模糊、CRF）；
    加上：这一段时间里在画的每个镜头（按 pre/post 和通用转场算出的实际绘制范围）所在 shots 文件的内容。
  所以改一个镜头文件，只重渲这个文件里的镜头覆盖的段；改公共文件或时间轴，整片重渲。
  一个镜头用到另一个镜头文件里定义的函数时，把这个函数挪进 shots_00_*（共用文件），否则改了它不会触发重渲。
  被中断后重跑，也会跳过已完成的分段。
每一帧在页面里一次做完：画 t（顺带读引擎登记的镜头矩阵 __CAMS / __GLOBAL / __FRAME、画面事件 __ACTS、放不下的文字块 __TEXTFIT、
  同框文字冲突 __TEXTCLASH，以及新出现的字）→ 读画布。每段的登记存成 <段>.track.json，渲完拼成 out/segments/<档>_track.json 交给体检，
  抖动和短句对齐都读它，不再为检查另跑一遍。
运动模糊：正式档总是打开，采样数由引擎按画面变化定（motion_blur.samples 是下限，max 是上限）：快门两端几乎一样的帧只画一次，
  在动的帧逐级加倍采样直到结果稳定。草稿档关闭（window.__MB_OFF）。正式档完成时打印平均每帧采样数和最多用到几次（引擎的 __MBSTAT）。
正式档出完，体检（checkup.py）会把它和草稿档逐帧比对找重影（tools/ghostcheck.py）；草稿档早于当前代码时跳过，并提示先重渲草稿档。
  加了 --no-checkup 时只单独跑这项比对。
速度：读画布比浏览器截图快约 5 倍（截图每帧固定约 33 毫秒，等合成器出帧；读画布草稿 3 毫秒、正式 8 毫秒）。没开 shader 的讲解片草稿档
  每进程约 60–75 帧/秒，90 秒的片子渲染约 10 秒，加预检和体检约 20 秒。某进程连续 30 秒低于 1 帧/秒会报警，通常是整机 GPU 被抢。
色彩：画布 JPEG 是 sRGB 全范围（和浏览器截图逐字节相同），用 bt601→rgb→bt709 链路转受限范围，直接用 out_color_matrix=bt709 会整体偏暗约 4 级。
"""
import sys, os, time, subprocess, json, hashlib, math, re
from multiprocessing import Process, Queue
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
from common import ROOT, ffmpeg, project, timeline, serve, open_page, pop_format, out_name, uses_gpu, gpu_slot, formats, probe, probe_line, TRACK_JS, FRAME_JS, TRACK_FLUSH_JS

ARGV = sys.argv[1:]
FMTS = pop_format(ARGV)
def flag(n):
    if n in ARGV: ARGV.remove(n); return True
    return False
def opt(n, d=None):
    if n in ARGV: i = ARGV.index(n); v = ARGV[i + 1]; del ARGV[i:i + 2]; return v
    return d
FINAL, MASTER, SHARE, FRESH, NO_PRE, NO_CHECK, NO_SYNC = (flag(n) for n in ('--final', '--master', '--share', '--fresh', '--no-preflight', '--no-checkup', '--no-sync'))
if (MASTER or SHARE) and not FINAL: sys.exit('--master、--share 只用于正式档，和 --final 一起用')
CFG = project(); GPU = uses_gpu(CFG)
NPROC = int(opt('-j', 3 if GPU else 4))
_bad = [a for a in ARGV if a.startswith('-')]
if _bad or len(ARGV) not in (0, 2): sys.exit(f'看不懂参数：{" ".join(ARGV)}（python3 tools/render.py --help 看用法）')


# ---------------------------------------------------------------- 渲染前同步：时间轴、音效事件、混音
def _mt(p): return p.stat().st_mtime if p.exists() else 0


def _run(args, what):
    print(f'[同步] {what}：python3 {" ".join(args)}', flush=True)
    r = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True)
    tail = [l for l in ((r.stdout or '') + (r.stderr or '')).strip().splitlines() if l.strip()][-4:]
    for l in tail: print('  ' + l)
    if r.returncode: sys.exit(f'[同步] {args[0]} 没跑通，没有开始渲染。照上面的提示改好后重跑（确认不要同步时加 --no-sync）。')


def sync():
    """时间轴：project.json、script/vo.json、audio/narration.wav 比 timeline.json 新，或 web/ 有没登记进 index.html 的 shots_*.js 时，重跑 timeline.py。
    声音：页面代码或时间轴比 audio/events.json 新时重新导出音效事件；事件、时间轴、project.json、人声、audio/ 下的脚本和 mix_final.wav
    记一个签名（audio/.mix_sig），签名变了或 mix_final.wav 不在时重跑 audio/synth.py。"""
    tl = ROOT / 'timeline.json'; web = ROOT / 'web'
    srcs = [ROOT / n for n in ('project.json', 'script/vo.json', 'audio/narration.wav')]
    newer = [p.relative_to(ROOT).as_posix() for p in srcs if p.exists() and _mt(p) > _mt(tl) + 0.5]
    idx = (web / 'index.html').read_text(encoding='utf-8') if (web / 'index.html').exists() else ''
    unreg = [f.name for f in sorted(web.glob('shots_*.js')) if f.name not in idx]
    if newer or unreg or not tl.exists():
        voice = (CFG.get('timeline') or {}).get('mode', 'voice') == 'voice'
        est = voice and not (ROOT / 'audio' / 'narration.wav').exists()
        _run(['tools/timeline.py'] + (['--estimate'] if est else []), '时间轴过期（' + '、'.join(newer + [f'{n} 没登记' for n in unreg] or ['没有 timeline.json']) + '）')
    ev = ROOT / 'audio' / 'events.json'
    code = [p for p in web.rglob('*') if p.is_file() and p.suffix in ('.js', '.html')] + [tl]
    if _mt(ev) < max(map(_mt, code)) - 0.5:
        _run(['tools/dump_events.py'], '页面代码比音效事件新，重新导出')
    h = hashlib.sha1()
    for p in [ev, tl, ROOT / 'project.json'] + sorted((ROOT / 'audio').glob('*.py')):
        if p.exists(): h.update(p.name.encode()); h.update(p.read_bytes())
    for p in [ROOT / 'audio' / 'voice_aligned.wav'] + [ROOT / f for f in [(CFG.get('music') or {}).get('file')] if f]:
        if p.exists(): st = p.stat(); h.update(f'{p.name}:{st.st_size}:{st.st_mtime_ns}'.encode())
    sig = h.hexdigest(); sf = ROOT / 'audio' / '.mix_sig'; mix = ROOT / 'audio' / 'mix_final.wav'
    if not mix.exists() or not sf.exists() or sf.read_text().strip() != sig:
        _run(['audio/synth.py'], '音效事件、时间轴或配乐设置变了' if mix.exists() else '还没有 audio/mix_final.wav')
        sf.write_text(sig)


if not NO_SYNC:
    sync()
TOTAL = timeline()['total']
FPS = CFG.get('fps', 60) if FINAL else min(30, CFG.get('fps', 60))
SCALE = 1.0 if FINAL else 0.5
CRF = 14 if MASTER else 18 if FINAL else 28
PRESET = 'medium' if FINAL else 'fast'
MODE = 'master' if MASTER else 'final' if FINAL else 'draft'
CHUNK = 4.0                                                # 长镜头切成不超过约 4 秒的段
PART = len(ARGV) >= 2
OUT = ROOT / 'out'; SEG = OUT / 'segments'; SEG.mkdir(parents=True, exist_ok=True)
VF = ('scale=in_range=pc:in_color_matrix=bt601:flags=accurate_rnd+full_chroma_int,format=rgb24,'
      'scale=trunc(iw/2)*2:trunc(ih/2)*2:out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int')
PRE_JS = r"""
(() => {
  window.__NAN = []; window.__T = 0;
  const P = CanvasRenderingContext2D.prototype;
  const bad = v => typeof v === 'number' ? !isFinite(v) : (v instanceof DOMMatrix ? ![v.a, v.b, v.c, v.d, v.e, v.f].every(isFinite) : false);
  const note = (fn, i, v) => { if (window.__NAN.length < 40) window.__NAN.push({ fn, arg: i, v: String(v), t: window.__T }); };
  for (const n of ['moveTo', 'lineTo', 'arc', 'arcTo', 'ellipse', 'rect', 'roundRect', 'fillRect', 'strokeRect', 'clearRect', 'drawImage', 'translate', 'scale', 'rotate',
                   'transform', 'setTransform', 'bezierCurveTo', 'quadraticCurveTo', 'fillText', 'strokeText', 'createLinearGradient', 'createRadialGradient']) {
    const o = P[n]; if (!o) continue;
    P[n] = function () { for (let i = 0; i < arguments.length; i++) if (bad(arguments[i])) { note('ctx.' + n, i + 1, arguments[i]); break; } return o.apply(this, arguments); };
  }
  for (const prop of ['globalAlpha', 'lineWidth', 'shadowBlur']) {
    const d = Object.getOwnPropertyDescriptor(P, prop);
    if (d && d.set) Object.defineProperty(P, prop, { get: d.get, set(v) { if (typeof v === 'number' && !isFinite(v)) note('ctx.' + prop + ' =', 0, v); d.set.call(this, v); }, configurable: true, enumerable: d.enumerable });
  }
})();
"""
# 每个镜头的实际绘制范围（pre/post、a/b、通用转场），和 main.js 的算法一致；以及页面上登记的全局效果
RANGES_JS = r"""() => {
  const order = Object.values(TL.scenes).sort((x, y) => x.t0 - y.t0), TR = (window.PROJECT || {}).transitions || {};
  const trOf = i => { const s = order[i]; if (!order[i + 1]) return null; const v = TR[s.id] ?? TR.default ?? 'cut'; const o = typeof v === 'string' ? { type: v } : v; return o.type === 'cut' ? null : Object.assign({ dur: 0.5 }, o); };
  const ranges = order.map((S, i) => {
    const d = window.SHOT[S.id];
    let a = d && d.a !== undefined ? d.a : S.t0 - ((d && d.pre) || 0), z = d && d.b !== undefined ? d.b : S.t1 + ((d && d.post) || 0);
    const tin = i > 0 ? trOf(i - 1) : null, tout = trOf(i);
    if (tin) a = Math.min(a, S.t0 - tin.dur / 2);
    if (tout) z = Math.max(z, S.t1 + tout.dur / 2);
    return [S.id, a, z];
  });
  const g = n => { try { return eval(n); } catch (e) { return null; } };
  return { ranges, globals: JSON.stringify([g('SHAKES'), g('FLASH'), g('CUTS'), g('FAST')]) };
}"""
FRAME_TIMEOUT_MS = 30000; MAX_RESTARTS = 4
TEXT_EXT = {'.js', '.html', '.css', '.json', '.glsl', '.wgsl', '.frag', '.vert', '.txt', '.svg'}


# ---------------------------------------------------------------- 指纹
def shot_files():
    """(公共镜头文件列表, {镜头 id: [定义它的文件]})。shots_00_* 和不定义 SHOT 的文件算公共。"""
    common, owner = [], {}
    for f in sorted((ROOT / 'web').glob('shots_*.js')):
        ids = re.findall(r'SHOT\s*(?:\.\s*(\w+)|\[\s*[\'"](\w+)[\'"]\s*\])\s*=', f.read_text(encoding='utf-8'))
        ids = {a or b for a, b in ids}
        if f.name.startswith('shots_00') or not ids: common.append(f)
        else:
            for i in ids: owner.setdefault(i, []).append(f)
    return common, owner


def file_digest(h, p):
    h.update(str(p.relative_to(ROOT)).encode())
    if p.suffix.lower() in TEXT_EXT and p.stat().st_size < 8_000_000: h.update(p.read_bytes())
    else: st = p.stat(); h.update(f'{st.st_size}:{st.st_mtime_ns}'.encode())   # 字体、图片、视频：只记清单


def common_hash(globals_json, params):
    h = hashlib.sha1(); common, _ = shot_files(); shots = {f for f in (ROOT / 'web').glob('shots_*.js')} - set(common)
    for p in sorted((ROOT / 'web').rglob('*')):
        if p.is_file() and p not in shots: file_digest(h, p)
    for n in ('project.json', 'timeline.json'):
        if (ROOT / n).exists(): file_digest(h, ROOT / n)
    h.update(globals_json.encode()); h.update(json.dumps(params, sort_keys=True).encode())
    return h.hexdigest()


def plan(F0, F1, ranges, base, owner):
    """按镜头边界切段，长段再切开。返回 [(f0, f1, [镜头], 指纹)]。"""
    cuts = {F0, F1} | {int(round(s['t0'] * FPS)) for s in timeline()['scenes'].values()}
    edges = sorted(c for c in cuts if F0 <= c <= F1)
    segs = []
    for a, z in zip(edges, edges[1:]):
        n = max(1, math.ceil((z - a) / (CHUNK * FPS) - 1e-9))
        for k in range(n): segs.append((a + (z - a) * k // n, a + (z - a) * (k + 1) // n))
    out, cache = [], {}
    for a, z in segs:
        if z <= a: continue
        ta, tz = (a - 0.5) / FPS, z / FPS                     # 运动模糊子帧最多越过帧时刻半帧（快门 ≤ 1）
        live = [i for i, ra, rz in ranges if ra < tz - 1e-9 and rz > ta + 1e-9]
        h = hashlib.sha1(base.encode())
        for i in live:
            for f in owner.get(i, []):
                if f not in cache: cache[f] = hashlib.sha1(f.read_bytes()).hexdigest()
                h.update(f'{i}:{f.name}:{cache[f]}'.encode())
        out.append((a, z, live, h.hexdigest()[:20]))
    return out


# ---------------------------------------------------------------- 渲染进程
def worker(url, fmt, queue, tag, wid):
    """queue 里是 (f0, f1, 指纹)：一个进程开一次浏览器，从共享队列里一段接一段地取，直到取完（快的进程多渲几段，不会有一个进程拖到最后）。
    每帧一次页面调用：画 t（正式档带运动模糊，顺带读引擎的登记）→ 直接读画布编码 JPEG。
    每段的登记存成 <段>.track.json，和分段一起复用，体检用它查抖动、画面事件和文字块。"""
    from playwright.sync_api import sync_playwright
    import contextlib, base64
    log = open(SEG / f'{tag}_w{wid}.log', 'w')
    def say(s, echo=False):
        log.write(s + '\n'); log.flush()
        if echo: print(f'[进程{wid}] {s}', flush=True)
    def jobs():
        while True:
            j = queue.get()
            if j is None: return                                   # 每个进程一个结束标记
            yield j
    t_all = time.time(); total = 0; done_n = 0
    lease = gpu_slot(lambda s: say(s, True)) if GPU else contextlib.nullcontext()
    q = 95 if FINAL else 85
    with lease, sync_playwright() as p:
        h = pg = None
        def page():
            nonlocal h, pg
            if h: h.close()
            h, pg, errs = open_page(p, url, fmt, scale=SCALE, init_script=TRACK_JS)
            return errs
        errs = page(); say(f'{time.time() - t_all:.1f}s 页面就绪')
        for f0, f1, sig in jobs():
            total += f1 - f0
            path = SEG / f'{tag}_{f0:06d}-{f1:06d}.mp4'
            enc = subprocess.Popen([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(FPS), '-i', '-',
                                    '-vf', VF, '-c:v', 'libx264', '-preset', PRESET, '-crf', str(CRF),
                                    '-pix_fmt', 'yuv420p', '-r', str(FPS), '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709',
                                    '-color_trc', 'bt709', '-x264-params', f'keyint={FPS * 2}', str(path)], stdin=subprocess.PIPE)
            pg.evaluate(TRACK_FLUSH_JS); say(f'{time.time() - t_all:.1f}s 开始第 {f0}–{f1} 帧')
            i, restarts, recs = f0, 0, []; last_t, last_i, slow_since = time.time(), f0, None
            while i < f1:
                t = i / FPS
                r = pg.evaluate(FRAME_JS, [t, q, SCALE, FINAL, FRAME_TIMEOUT_MS])
                if r is None:
                    restarts += 1; say(f'!! 第 {i} 帧超时（GPU 卡死），第 {restarts} 次重启，从该帧续渲', True)
                    if restarts > MAX_RESTARTS:
                        say('重启次数超限，放弃', True); enc.stdin.close(); enc.wait(); h.close(); sys.exit(2)
                    errs = page(); pg.evaluate(TRACK_FLUSH_JS); continue
                enc.stdin.write(base64.b64decode(r[0].split(',', 1)[1])); recs.append(r[1]); i += 1
                now = time.time()
                if now - last_t >= 5:
                    fps = (i - last_i) / (now - last_t); say(f'{done_n + i - f0} 帧  {fps:.1f} 帧/秒')
                    if fps < 1:
                        slow_since = slow_since or last_t
                        if now - slow_since > 30:
                            say(f'!! 连续 {now - slow_since:.0f} 秒低于 1 帧/秒。常见原因：整机同时有多个渲染在用 GPU（shader 背景），或运动模糊子帧太多。', True)
                            slow_since = now
                    else:
                        slow_since = None
                    last_t, last_i = now, i
            enc.stdin.close(); enc.wait()
            if enc.returncode: say(f'ffmpeg 编码失败（第 {f0}–{f1} 帧）', True); h.close(); sys.exit(3)
            extra = pg.evaluate(TRACK_FLUSH_JS)
            json.dump(dict(extra, frames=recs), open(SEG / f'{tag}_{f0:06d}-{f1:06d}.track.json', 'w'), ensure_ascii=False, separators=(',', ':'))
            (SEG / f'{tag}_{f0:06d}-{f1:06d}.done').write_text(json.dumps({'sig': sig, 'f0': f0, 'f1': f1}))
            done_n += f1 - f0
        if errs: say('页面错误 ' + json.dumps(errs[:5], ensure_ascii=False), True)
        h.close(); el = time.time() - t_all
        say(f'完成 {total} 帧，用时 {el:.0f} 秒，平均 {total / max(1e-6, el):.1f} 帧/秒', True)
        # 分段和日志都已落盘。几个进程同时杀掉 Chrome 后，Playwright 收尾偶尔要等约 30 秒连接超时；子进程直接退出，不等它
        log.close(); sys.stdout.flush(); os._exit(0)


def spans(ids_list):
    """把连续的同一组镜头合并成可读的说明"""
    out = []
    for a, z, ids in ids_list:
        key = '+'.join(ids) or '（空）'
        if out and out[-1][2] == key and abs(out[-1][1] - a) < 1e-6: out[-1][1] = z
        else: out.append([a, z, key])
    return '；'.join(f'{k} {a:.1f}–{z:.1f}s' for a, z, k in out)


def render_format(fmt, url, info):
    if PART:
        F0, F1 = int(round(float(ARGV[0]) * FPS)), int(round(float(ARGV[1]) * FPS)); kind = f'part_{ARGV[0]}-{ARGV[1]}'
    else:
        F0, F1 = 0, int(round(TOTAL * FPS)); kind = 'full'
    tag = f'{kind}_{fmt}_{MODE}'
    _, owner = shot_files()
    base = common_hash(info['globals'], {'fps': FPS, 'scale': SCALE, 'mb': FINAL, 'crf': CRF, 'preset': PRESET, 'fmt': fmt, 'size': list(formats()[fmt])})
    segs = plan(F0, F1, info['ranges'], base, owner)
    keep, todo, reused = set(), [], []
    for a, z, live, sig in segs:
        name = f'{tag}_{a:06d}-{z:06d}'; keep.add(name)
        d, m = SEG / f'{name}.done', SEG / f'{name}.mp4'
        if not FRESH and d.exists() and m.exists() and (SEG / f'{name}.track.json').exists() and json.loads(d.read_text()).get('sig') == sig:
            reused.append((a / FPS, z / FPS, live)); continue
        d.unlink(missing_ok=True); todo.append((a, z, live, sig))
    for f in SEG.glob(f'{tag}_*'):                         # 时间轴变了以后留下的旧分段（.mp4 / .done / .track.json）
        stem = f.name.split('.')[0]
        if re.fullmatch(re.escape(tag) + r'_\d{6}-\d{6}', stem) and stem not in keep: f.unlink()
    print(f'{fmt}：{len(segs)} 段（按镜头切），复用 {len(reused)} 段，重渲 {len(todo)} 段')
    if reused: print(f'  复用：{spans(reused)}')
    if todo: print(f'  重渲：{spans([(a / FPS, z / FPS, live) for a, z, live, _ in todo])}')
    g = json.loads(info['globals']); shakes, fast = g[0] or [], g[3] or []
    T = time.time()
    if todo:
        n = max(1, min(NPROC, len(todo)))
        q = Queue()
        for a, z, live, sig in sorted(todo, key=lambda j: j[0] - j[1]): q.put((a, z, sig))   # 长的段先取
        for _ in range(n): q.put(None)
        ps = [Process(target=worker, args=(url, fmt, q, tag, w)) for w in range(n)]
        for p in ps: p.start()
        for p in ps: p.join()
        if any(p.exitcode for p in ps): sys.exit(f'有分段失败，看 {SEG}/{tag}_w*.log')
        print(f'{fmt}：渲染 {sum(z - a for a, z, _, _ in todo)} 帧用时 {time.time() - T:.0f} 秒（{len(ps)} 个进程，{FPS} 帧/秒，{"正式档" if FINAL else "草稿档"}）')
    lst = SEG / f'{tag}_list.txt'
    lst.write_text(''.join(f"file '{SEG}/{tag}_{a:06d}-{z:06d}.mp4'\n" for a, z, _, _ in segs))
    track = SEG / f'{tag}_track.json'                       # 各段的登记按时间拼起来，交给体检
    parts = [json.load(open(SEG / f'{tag}_{a:06d}-{z:06d}.track.json')) for a, z, _, _ in segs]
    json.dump({'fps': FPS, 'size': list(formats()[fmt]), 'shakes': shakes, 'fast': fast, 'segments': [[a / FPS, z / FPS] for a, z, _, _ in segs],
               'frames': [r for q in parts for r in q['frames']], 'texts': [x for q in parts for x in q['texts']],
               'acts': [x for q in parts for x in q['acts']], 'fits': [x for q in parts for x in q['fits']], 'clash': [x for q in parts for x in q.get('clash') or []],
               'overlaps': [x for q in parts for x in q.get('overlaps') or []]},
              open(track, 'w'), ensure_ascii=False, separators=(',', ':'))
    video = SEG / f'{tag}_video.mp4'
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(video)], check=True)
    suffix = '_master' if MASTER else '' if FINAL else '_draft'
    final = OUT / (out_name(fmt, suffix) if not PART else f"{kind}{'_' + fmt if len(formats()) > 1 else ''}{suffix}.mp4")
    audio = ROOT / 'audio' / 'mix_final.wav'
    cmd = [ffmpeg(), '-y', '-loglevel', 'error', '-i', str(video)]
    if audio.exists():
        cmd += ['-ss', str(F0 / FPS), '-t', str((F1 - F0) / FPS), '-i', str(audio), '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k']
    cmd += ['-c:v', 'copy', '-movflags', '+faststart', '-shortest', str(final)]
    subprocess.run(cmd, check=True)
    print('成片：' + probe_line(probe(final)) + ('' if audio.exists() else '（没有 audio/mix_final.wav，所以无声）'))
    if FINAL:
        ms = [q.get('mbstat') for q in parts]
        if all(ms) and sum(m['frames'] for m in ms):
            nf, ns = sum(m['frames'] for m in ms), sum(m['samples_total'] for m in ms)
            nd = sum(m.get('draws_total') or 0 for m in ms)
            print(f'运动模糊：平均每帧 {ns / nf:.1f} 次采样，最多用到 {max(m["max_used"] for m in ms)} 次（{nf} 帧，静止帧只采一次' + (f'；连判断在内平均每帧画 {nd / nf:.1f} 次' if nd else '') + '）')
        else:
            print('运动模糊：引擎没有登记采样统计（window.__MBSTAT），或有分段是旧版引擎渲的（加 --fresh 重渲可得到完整统计）')
    if SHARE and not PART:
        share = OUT / out_name(fmt, '_share')
        subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', str(final), '-c:v', 'libx264', '-preset', 'medium', '-b:v', '6M', '-maxrate', '7M',
                        '-bufsize', '12M', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', str(share)], check=True)
        print('分享版：' + probe_line(probe(share)))
    return final, track


# ---------------------------------------------------------------- 渲染前检查
def page_info(url, fmt, t_from, t_to, check):
    """打开页面：check 为真时按 0.25 秒调用 render(t) 做预检。返回 (问题列表 [(时刻, 说明)], 镜头绘制范围和全局效果)。"""
    import contextlib
    from playwright.sync_api import sync_playwright
    lease = gpu_slot() if GPU else contextlib.nullcontext()
    found, seen = [], set()
    def add(t, msg):
        key = msg[:80]
        if key not in seen: seen.add(key); found.append((t, msg))
    ts, t = [], t_from
    while t < t_to - 1e-9: ts.append(round(t, 4)); t += 0.25
    ts.append(round(max(t_from, min(t_to, TOTAL) - 1 / FPS), 4))
    with lease, sync_playwright() as p:
        h, pg, errs = open_page(p, url, fmt, init_script=PRE_JS if check else None)
        try:
            info = pg.evaluate(RANGES_JS)
            if check:
                pg.evaluate('window.__MB_OFF = true')
                for e in errs:
                    if not e.startswith('console.warning'): add(0.0, '页面加载时报错：' + e)
                for t in ts:
                    n0 = len(errs); pg.evaluate(f'window.__T = {t}')
                    try: pg.evaluate(f'render({t})')
                    except Exception as e: add(t, 'JS 抛错：' + str(e).strip().split('\n')[0][:240])
                    for e in errs[n0:]:
                        if not e.startswith('console.warning'): add(t, e[:240])
                for n in pg.evaluate('window.__NAN'):
                    add(n['t'], f"画布调用 {n['fn']} 的第 {n['arg']} 个参数是 {n['v']}（画布遇到它不报错，只是这一笔不画）" if n['arg'] else f"画布属性 {n['fn']} {n['v']}（设置无效，保持上一个值）")
        finally:
            h.close()
    return sorted(found), info


GATE = ('文字出框', '文字互相压住', '标注没落到目标')       # 渲整片前就拦的版面硬伤；字太小等留给渲染后的体检
SUMMARY_N = 12


def layout_gate(fmt):
    """整片渲染前查版面，有阻断问题就停。返回版面结果文件（交给体检复用）。"""
    name = 'prerender' + (f'_{fmt}' if len(formats()) > 1 else '')
    jp = ROOT / 'frames' / '_view' / f'{name}_layout.json'; jp.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, 'tools/layout.py', 'prerender', '--format', fmt], cwd=ROOT, capture_output=True, text=True)
    if not jp.exists():
        print(f'[版面] {fmt} 版面审计没跑完：\n' + ((r.stdout or '') + (r.stderr or ''))[-1500:]); sys.exit(1)
    items = json.load(open(jp))['items']
    bad = [it for it in items if it.get('level') == '❌' and it['issue'].startswith(GATE)]
    if bad:
        print(f'[版面] {fmt} 有 {len(bad)} 个问题，没有开始渲染：')
        for it in bad[:12]: print('  ' + it['line'])
        sys.exit('照每条的文件和行号改好后重跑（python3 tools/layout.py 可单独查，问题帧在 frames/_view/）；确认要跳过检查时加 --no-preflight。')
    warn = sum(1 for it in items if it.get('level') == '⚠️')
    info = sum(1 for it in items if it.get('level') == 'ℹ️')
    print(f'[版面] {fmt} 通过（没有字出框、字压字、没落到目标的标注）' + (f'；{warn} 条 ⚠️ 留给渲染后的体检' if warn else '') + (f'；可选提示 {info} 条' if info else ''))
    return jp


def checkup(fmt, video, track, lay):
    """渲完跑体检，终端只打印摘要：条数、前几条问题（带文件行号）、总览图和报告的路径。"""
    cmd = [sys.executable, 'tools/checkup.py', '--format', fmt, '--video', str(video), '--track', str(track)] + (['--layout', str(lay)] if lay else [])
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = ROOT / 'frames' / '_view' / ('checkup' + (f'_{fmt}' if len(formats()) > 1 else ''))
    jp = out / 'checkup.json'
    if r.returncode or not jp.exists():
        print(f'[体检] {fmt} 没跑完：\n' + ((r.stdout or '') + (r.stderr or ''))[-1500:]); return
    res = json.load(open(jp))
    iss = res['issues']; nb = sum(1 for x in iss if x['level'] == '❌'); nw = sum(1 for x in iss if x['level'] == '⚠️')
    hard = [x for x in iss if x['level'] in ('❌', '⚠️')]
    print(f'\n[体检] {fmt}：硬伤 {nb + nw} 条（❌ {nb}、⚠️ {nw}）；可选提示 {len(iss) - len(hard)} 条见报告（{res["elapsed"]:.0f} 秒）')
    for x in hard[:SUMMARY_N]: print('  ' + x['line'])
    if len(hard) > SUMMARY_N: print(f'  …还有 {len(hard) - SUMMARY_N} 条，见报告')
    print(f'  总览图：{out / "总览.jpg"}（编号和上面的清单对应）')
    if (out / '对齐.jpg').exists(): print(f'  对齐图：{out / "对齐.jpg"}（短句、画面事件、画面变化量）')
    print(f'  报告：{out / "报告.md"}')


def main():
    import lint
    found = lint.lint()
    if found: lint.report(found); sys.exit(1)
    print('[合同预检] 通过')
    a, z = (float(ARGV[0]), float(ARGV[1])) if PART else (0.0, TOTAL)
    infos, lays = {}, {}
    with serve() as url:
        for fmt in FMTS:
            bad, infos[fmt] = page_info(url, fmt, a, z, not NO_PRE)
            if bad:
                print(f'[预检] {fmt} 画幅有 {len(bad)} 个问题，没有开始渲染：')
                for t, msg in bad[:12]: print(f'  t = {t:.2f} 秒  {msg}')
                sys.exit('修好后重跑；确认要跳过检查时加 --no-preflight。')
        if not NO_PRE: print('[预检] 通过（每 0.25 秒调用一次 render(t)，没有 JS 报错和 NaN 参数）')
        if not NO_PRE and not PART:
            for fmt in FMTS: lays[fmt] = layout_gate(fmt)
        finals = {fmt: render_format(fmt, url, infos[fmt]) for fmt in FMTS}
    if PART: return
    if NO_CHECK:
        if FINAL:                                                  # 不跑体检时，正式档仍和草稿档比一次重影
            sys.stdout.flush()
            for fmt in FMTS: subprocess.run([sys.executable, 'tools/ghostcheck.py', '--format', fmt, '--final', str(finals[fmt][0])], cwd=ROOT)
    else:
        for fmt in FMTS: checkup(fmt, *finals[fmt], lays.get(fmt))
    if FINAL:                                                      # 交付核对：成片事实 + 硬约束清单 → out/交付核对.md
        sys.stdout.flush(); print()
        r = subprocess.run([sys.executable, 'tools/deliver.py', '--format', ','.join(FMTS)], cwd=ROOT, capture_output=True, text=True)
        print(r.stdout.rstrip() if r.returncode == 0 else '[交付核对] 没跑完：\n' + ((r.stdout or '') + (r.stderr or ''))[-1500:])


if __name__ == '__main__':
    main()
