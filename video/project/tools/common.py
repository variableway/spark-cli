"""公共：工程根目录、project.json、画幅、本地 http 服务、Chrome 启动、整机 GPU 名额、ffmpeg、
成片信息（probe，不需要 ffprobe）和解码（decode、frame_at）、报告图用的中文字体（font）、
取画面（snap：直接读画布，不走浏览器截图）、渲染时顺带记录的画面登记（TRACK_JS / FRAME_JS）。"""
import json, os, re, sys, time, platform, threading, socketserver, http.server, contextlib, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def project():
    return json.load(open(ROOT / 'project.json', encoding='utf-8'))


def timeline():
    return json.load(open(ROOT / 'timeline.json', encoding='utf-8'))


def vo():
    """配音稿：[(id, text)]，以及 tts_fix"""
    d = json.load(open(ROOT / 'script' / 'vo.json', encoding='utf-8'))
    return [(s['id'], s['text']) for s in d['scenes']], d.get('tts_fix', {})


def vo_tr():
    """配音稿的译文：{镜头: {语言代码: [每个短句一条]}}。vo.json 里每个镜头可写 "en": ["...", "..."]（别的语言同理，键是语言代码），
    按 syl.phrases 切出的短句一一对应（按，。；：？！、和 <#停顿#> 切）。build_timeline.py 写进 timeline.json 的短句，字幕层和 srt.py 都读它。"""
    d = json.load(open(ROOT / 'script' / 'vo.json', encoding='utf-8'))
    return {s['id']: {k: v for k, v in s.items() if k not in ('id', 'text') and re.fullmatch(r'[a-z]{2}(?:-[A-Za-z]+)?', k)} for s in d['scenes']}


def voice_lang(text):
    """配音短句的语言：有汉字算 zh，否则算 en（和引擎字幕层同一规则）"""
    return 'zh' if re.search(r'[\u4e00-\u9fff]', text) else 'en'


def subtitles(cfg=None):
    """project.json 的 subtitles（字幕层）：{burn, langs, ...}；没写时 burn = False，langs = ['zh']"""
    s = dict((cfg or project()).get('subtitles') or {})
    s.setdefault('burn', False); s.setdefault('langs', ['zh'])
    return s


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path):
    """成片信息，用 imageio-ffmpeg 自带的 ffmpeg 读（不需要 ffprobe）：
    {path, duration 秒, width, height, fps, audio 有没有音轨, audio_sec 音轨时长, mb 文件大小}"""
    import re, subprocess
    s = subprocess.run([ffmpeg(), '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    d = re.search(r'Duration: (\d+):(\d+):([\d.]+)', s)
    v = re.search(r'Video: [^\n]*?(\d{2,5})x(\d{2,5})[^\n]*?([\d.]+) fps', s)
    info = dict(path=str(path), duration=round(int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)), 3) if d else None,
                width=int(v.group(1)) if v else None, height=int(v.group(2)) if v else None, fps=float(v.group(3)) if v else None,
                audio=bool(re.search(r'Stream #[^\n]*Audio:', s)), audio_sec=None, mb=round(os.path.getsize(path) / 1e6, 1))
    if info['audio']:                                             # 音轨时长：把音轨原样走一遍，读最后的 time=
        r = subprocess.run([ffmpeg(), '-hide_banner', '-i', str(path), '-map', '0:a:0', '-c', 'copy', '-f', 'null', '-'], capture_output=True, text=True).stderr
        ts = re.findall(r'time=(\d+):(\d+):([\d.]+)', r)
        if ts: h_, m_, s_ = ts[-1]; info['audio_sec'] = round(int(h_) * 3600 + int(m_) * 60 + float(s_), 2)
    return info


def probe_line(info):
    """一行成片信息：路径、时长、画幅、帧率、音轨、大小"""
    au = (f"有音轨（{info['audio_sec']:.1f} 秒）" if info['audio_sec'] is not None else '有音轨') if info['audio'] else '无音轨'
    return f"{info['path']}　{info['duration']:.2f} 秒　{info['width']}×{info['height']}　{info['fps']:g} 帧/秒　{au}　{info['mb']:.1f} MB"


def decode(path, w, h, fps=None, gray=True, batch=240):
    """按批解码成 numpy：每批 (n, h, w) 灰度或 (n, h, w, 3) RGB。fps 给了就按这个帧率取帧（ffmpeg 的 fps 滤镜）。长片不会一次占满内存。"""
    import subprocess
    import numpy as np
    vf = (f'fps={fps},' if fps else '') + f'scale={w}:{h}'
    c = 1 if gray else 3
    pr = subprocess.Popen([ffmpeg(), '-loglevel', 'error', '-i', str(path), '-vf', vf, '-pix_fmt', 'gray' if gray else 'rgb24', '-f', 'rawvideo', '-'],
                          stdout=subprocess.PIPE)
    size = w * h * c
    try:
        while True:
            raw = pr.stdout.read(size * batch)
            n = len(raw) // size
            if n == 0: break
            a = np.frombuffer(raw[:n * size], np.uint8)
            yield a.reshape((n, h, w) if gray else (n, h, w, 3))
    finally:
        pr.stdout.close(); pr.wait()


def frame_at(path, t, size=None):
    """成片在 t 秒的一帧（原尺寸 PIL 图；给 size 就缩放到这个尺寸）"""
    import io, subprocess
    from PIL import Image
    raw = subprocess.run([ffmpeg(), '-loglevel', 'error', '-ss', f'{max(0.0, t):.3f}', '-i', str(path), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True).stdout
    if not raw: return None
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    return im.resize(size, Image.LANCZOS) if size and im.size != tuple(size) else im


def font(size):
    """能显示中文的字体（报告图里的文字、标签）；找不到就用 PIL 默认字体（只显示英文和数字）"""
    from PIL import ImageFont
    for p in ('/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/STHeiti Medium.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
              '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'):
        try: return ImageFont.truetype(p, size)
        except Exception: continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- 画幅
def formats(cfg=None):
    """{名字: (w, h)}。没写 formats 时只有一个 'main'，尺寸取 canvas。"""
    cfg = cfg or project()
    c = cfg.get('canvas', {'w': 1920, 'h': 1080})
    f = cfg.get('formats')
    if not f:
        return {'main': (c['w'], c['h'])}
    return {k: (v['w'], v['h']) for k, v in f.items()}


def pop_format(argv):
    """从命令行取出 --format 名字（可写 all），返回 [名字, ...]；默认是第一个画幅。会从 argv 里删掉这两个参数。"""
    fm = formats()
    names = [next(iter(fm))]
    if '--format' in argv:
        i = argv.index('--format'); v = argv[i + 1]; del argv[i:i + 2]
        names = list(fm) if v == 'all' else v.split(',')
        for n in names:
            if n not in fm:
                sys.exit(f'没有这个画幅：{n}。可选：{", ".join(fm)}')
    return names


def out_name(fmt, suffix=''):
    """成片文件名：只有一个画幅时 <output>.mp4，多画幅时 <output>_<画幅>.mp4"""
    cfg = project(); base = cfg.get('output', 'video')
    multi = len(formats(cfg)) > 1
    return f"{base}{'_' + fmt if multi else ''}{suffix}.mp4"


def uses_gpu(cfg=None):
    cfg = cfg or project()
    return bool((cfg.get('background') or {}).get('preset')) or bool(cfg.get('gpu'))


# ---------------------------------------------------------------- 整机 GPU 名额
GPU_SLOTS = 3
_SLOT_DIR = Path(tempfile.gettempdir()) / 'motion_video_gpu_slots'


@contextlib.contextmanager
def gpu_slot(log=print):
    """整台机器最多 GPU_SLOTS 个使用 WebGPU 的 Chrome。超过 3 个时它们互相抢资源，速度会掉到 0.2 帧/秒。
    用文件锁领名额，进程退出时锁自动释放；领不到就排队等待。"""
    if os.name == 'nt':
        import msvcrt
        def lock(f):
            f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        def unlock(f):
            f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        def lock(f): fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def unlock(f): fcntl.flock(f, fcntl.LOCK_UN)
    _SLOT_DIR.mkdir(exist_ok=True)
    t0 = time.time(); warned = False
    while True:
        for i in range(GPU_SLOTS):
            f = open(_SLOT_DIR / f'slot{i}.lock', 'a+b')
            f.seek(0, 2)
            if f.tell() == 0: f.write(b'0'); f.flush()
            try:
                lock(f)
            except OSError:
                f.close(); continue
            try:
                yield i
            finally:
                unlock(f); f.close()
            return
        if not warned and time.time() - t0 > 5:
            log(f'GPU 名额已满（整机 {GPU_SLOTS} 个），排队等待…'); warned = True
        time.sleep(2)


# ---------------------------------------------------------------- 本地服务与浏览器
def chrome_args():
    a = ['--enable-gpu', '--enable-unsafe-webgpu', '--ignore-gpu-blocklist']
    if platform.system() == 'Darwin':
        a.append('--use-angle=metal')
    return a


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


@contextlib.contextmanager
def serve():
    """在 web/ 目录起一个本地 http 服务（端口随机），返回页面地址。页面要用 ES 模块和 fetch，file:// 不行。"""
    web = str(ROOT / 'web')
    handler = lambda *a, **k: _Quiet(*a, directory=web, **k)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), handler)
    srv.daemon_threads = True
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield f'http://127.0.0.1:{srv.server_address[1]}/index.html'
    finally:
        srv.shutdown()
        srv.server_close()


class Handle:
    """浏览器句柄。close() 关闭本次渲染创建的浏览器上下文（不碰用户自己的 Chrome）。
    shader 逐帧渲染后 Chrome 正常退出要等 GPU 资源回收，可能几分钟；只在产物落盘后调用。"""
    def __init__(self, ctx, udir):
        self.ctx, self.udir = ctx, udir

    def close(self):
        import shutil
        try:
            self.ctx.close()
        finally:
            shutil.rmtree(self.udir, ignore_errors=True)


def page_url(url, fmt):
    return url + (f'?format={fmt}' if fmt and fmt != 'main' else '')


def open_page(p, url, fmt=None, scale=1.0, ready_timeout=120000, init_script=None):
    """启动本机 Chrome（独立临时用户目录），按画幅设视口，打开页面，等 window.__ready。返回 (句柄, page, errors)。
    scale<1 时截图按比例缩小（草稿档用），画面内容不变。init_script：页面脚本运行之前注入的 JS（layout.py、render.py 预检用它包装画布调用）。"""
    fm = formats(); fmt = fmt or next(iter(fm))                  # 不指定画幅时用第一个
    w, h = fm[fmt]
    udir = tempfile.mkdtemp(prefix='mvs_chrome_')
    ctx = p.chromium.launch_persistent_context(udir, channel='chrome', headless=True, args=chrome_args(),
                                               viewport={'width': w, 'height': h}, device_scale_factor=scale)
    hd = Handle(ctx, udir)
    if init_script: ctx.add_init_script(init_script)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
    pg.on('console', lambda m: errs.append('console.' + m.type + ': ' + m.text[:300]) if m.type in ('error', 'warning') and 'favicon' not in m.text else None)
    pg.goto(page_url(url, fmt))
    try:
        pg.wait_for_function('window.__ready===true || !!window.__error', timeout=ready_timeout)
    except Exception:
        print('页面没有就绪。错误：', errs[:6]); hd.close(); sys.exit(1)
    if pg.evaluate('window.__error || null'):
        print('页面启动失败：', pg.evaluate('window.__error'), errs[:6]); hd.close(); sys.exit(1)
    return hd, pg, errs


# ---------------------------------------------------------------- 取画面
# 画面全部画在 canvas#c 上（shader 背景也是先画进它）。直接读画布编码 JPEG，和浏览器截图逐字节相同（同一个编码器、同样的缩小），
# 但不用等合成器出帧：截图每帧固定约 33 毫秒，读画布 3–8 毫秒。
SNAP_JS = r"""([q, s]) => { const c = document.getElementById('c'); let src = c;
  if (s !== 1) { const o = window.__SNAPCV || (window.__SNAPCV = document.createElement('canvas')), w = Math.round(c.width * s), h = Math.round(c.height * s);
    if (o.width !== w || o.height !== h) { o.width = w; o.height = h; }
    o.getContext('2d', { alpha: false }).drawImage(c, 0, 0, w, h); src = o; }
  return src.toDataURL('image/jpeg', q / 100); }"""


def snap(pg, t=None, q=85, scale=1.0):
    """（可选先 render(t)）读画布，返回 JPEG 字节。scale < 1 时在页面里缩小。"""
    import base64
    if t is not None: pg.evaluate(f'render({t})')
    return base64.b64decode(pg.evaluate(SNAP_JS, [q, scale]).split(',', 1)[1])


# ---------------------------------------------------------------- 渲染时顺带记录的画面登记
# 引擎每帧登记：window.__FRAME = {t, shots: [在画的镜头]}、window.__CAMS = {镜头: [a,b,c,d,e,f]}（cam() 相对 screen() 的变换）、
# window.__GLOBAL = [a..f]（全局后期变换：转场位移 + SHAKES）、window.__ACTS（act() 登记的画面事件）、window.__TEXTFIT（文字块放不下）、
# window.__TEXTCLASH（同一个框里两段字同时可见，后一段被推迟）、window.__MBSTAT（运动模糊每帧用了几次采样）。
# render.py 的渲染进程每帧读一次（在同一次页面调用里，不多花时间），按分段存成 *.track.json，体检直接用，不再为检查另跑一遍。
# 另外记下每段字第一次和最后一次被画出来的时刻（透明度 ≥ 0.5、非装饰字、非字幕：引擎画字幕时 ctx.__role = 'subtitle'），用来判断「这句话画面有没有新的字出现」；
# 并逐帧查同一种字（字体字号相同）的两段不同文字（透明度都 > 0.3、非装饰字）外框是否明显相交：横向、纵向各重叠到小的那段的 30% 以上，
# 交集超过小框面积 3%（相邻字母的字距重叠不算）。一段包含另一段（两字以上）的不算（同一行上叠画的高亮词）。换句时前一段还没退完、
# 后一段已经进来，版面审计的取样点常常碰不到这一两帧，逐帧查才看得到（只在草稿档查，正式档的运动模糊子帧会互相误判）。不同字体的叠放（列表从表头下滚过、标签贴在数字上）多半被裁剪
# 或卡片挡住，这里量不到遮挡，不查。按 镜头|两段字 记第一次、最后一次出现的时刻和帧数。
TRACK_JS = r"""
(() => {
  const P = CanvasRenderingContext2D.prototype;
  const alphaOf = c => {
    if (typeof c !== 'string') return 1; c = c.trim(); if (c === 'transparent') return 0;
    let m = /^(?:rgba|hsla)\(([^)]*)\)$/.exec(c); if (m) { const p = m[1].split(/[,\/\s]+/).filter(Boolean); return p.length >= 4 ? parseFloat(p[3]) * (p[3].endsWith('%') ? 0.01 : 1) : 1; }
    m = /^#([0-9a-f]{8}|[0-9a-f]{4})$/i.exec(c); if (m) { const h = m[1]; return h.length === 8 ? parseInt(h.slice(6), 16) / 255 : parseInt(h[3] + h[3], 16) / 255; }
    return 1;
  };
  const K = window.__TK = { on: false, t: 0, texts: new Map(), acts: new Map(), fits: new Map(), fitN: 0, clash: new Map(), boxes: [], ovl: new Map() };
  for (const name of ['fillText', 'strokeText']) {
    const o = P[name];
    P[name] = function (s, x, y) {
      if (K.on && !this.__deco && this.__role !== 'subtitle' && this.canvas && (this.canvas.id === 'c' || (K.mb && this.canvas.width === K.cw && this.canvas.height === K.ch))) {
        const a = this.globalAlpha * alphaOf(name === 'fillText' ? this.fillStyle : this.strokeStyle), str = String(s).trim();
        if (str && a > 0.3) {
          let sh = null; try { sh = typeof SHOT_NOW !== 'undefined' ? SHOT_NOW : null; } catch (e) {}
          if (a >= 0.5) { const k = (sh || '') + '\u0001' + str, e = K.texts.get(k); if (e) e[1] = K.t; else K.texts.set(k, [K.t, K.t]); }
          if (!K.mb && K.boxes.length < 400) {                       // 压字只在不开运动模糊时查：子帧之间的字互相比是误报
            const m = this.measureText(String(s)), T = this.getTransform(), X = [], Y = [];
            for (const u of [x - m.actualBoundingBoxLeft, x + m.actualBoundingBoxRight]) for (const v of [y - m.actualBoundingBoxAscent, y + m.actualBoundingBoxDescent]) {
              X.push(T.a * u + T.c * v + T.e); Y.push(T.b * u + T.d * v + T.f); }
            K.boxes.push([str, Math.min(...X), Math.min(...Y), Math.max(...X), Math.max(...Y), sh, this.font]);
          }
        }
      }
      return o.apply(this, arguments);
    };
  }
})();
"""
# 一帧：画 t（mb 为真 = 正式档，带运动模糊：采样数由引擎按画面变化自己定，静止帧只画一次；草稿档 window.__MB_OFF 只画一次），
# 顺带读引擎这一帧的登记（运动模糊时引擎留的是中间子帧的登记，离 t 最近）。运动模糊的子帧画在和主画布同尺寸的离屏画布上，那上面的字也记。
# 同框文字冲突 window.__TEXTCLASH（textBlock 把后一段推迟时登记）按 镜头|前一段|后一段 去重，记第一次出现的时刻。
# q = 0 时不编码（体检单独补登记时用）。返回 [jpeg dataURL 或 null, 登记]，超时返回 null。
FRAME_JS = r"""async ([t, q, s, mb, ms]) => {
  const K = window.__TK, guard = p => Promise.race([p.then(() => 1), new Promise(r => setTimeout(() => r(0), ms))]);
  const c = document.getElementById('c');
  K.t = t; K.on = true; K.mb = !!mb; K.cw = c.width; K.ch = c.height; K.boxes = []; window.__MB_OFF = !mb;
  const ok = await guard(render(t)); K.on = false; window.__MB_OFF = true; if (!ok) return null;
  const B = K.boxes;                                                           // 两段不同的字压在一起
  for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
    const p = B[i], q = B[j]; if (p[0] === q[0] || p[6] !== q[6]) continue;            // 只查同一种字（同字体字号）：两段同样的字在同一处交替
    if (Math.min(p[0].length, q[0].length) >= 2 && (p[0].includes(q[0]) || q[0].includes(p[0]))) continue;
    const iw = Math.min(p[3], q[3]) - Math.max(p[1], q[1]), ih = Math.min(p[4], q[4]) - Math.max(p[2], q[2]); if (iw <= 0 || ih <= 0) continue;
    const pw = p[3] - p[1], ph = p[4] - p[2], qw = q[3] - q[1], qh = q[4] - q[2];
    if (iw < 0.3 * Math.min(pw, qw) || ih < 0.3 * Math.min(ph, qh) || iw * ih <= 0.03 * Math.min(pw * ph, qw * qh)) continue;
    const [a, b] = p[0] < q[0] ? [p[0], q[0]] : [q[0], p[0]], sh = p[5] || q[5] || null, k = (sh || '') + '\u0001' + a + '\u0001' + b, e = K.ovl.get(k);
    if (e) { e.t1 = t; e.n++; } else K.ovl.set(k, { shot: sh, a, b, t0: t, t1: t, n: 1,
      box: [Math.min(p[1], q[1]), Math.min(p[2], q[2]), Math.max(p[3], q[3]), Math.max(p[4], q[4])].map(v => Math.round(v)) });
  }
  const F = window.__FRAME, C = window.__CAMS, G = window.__GLOBAL, shots = F && F.shots ? Array.from(F.shots) : null, cams = {};
  if (C) for (const k of Object.keys(C)) if (!shots || shots.includes(k)) cams[k] = Array.from(C[k]).map(v => +(+v).toFixed(4));
  const rec = [t, shots, cams, G ? Array.from(G).map(v => +(+v).toFixed(4)) : null];
  for (const a of (window.__ACTS || [])) { const k = a.name + '|' + a.at + '|' + a.shot; if (!K.acts.has(k)) K.acts.set(k, Object.assign({ seen: t }, a)); }
  const TF = window.__TEXTFIT || []; if (TF.length < K.fitN) K.fitN = 0;
  for (let i = K.fitN; i < TF.length; i++) { const f = TF[i], k = f.shot + '|' + f.text; if (!K.fits.has(k)) K.fits.set(k, Object.assign({ seen: t }, f)); }
  K.fitN = TF.length;
  const TC = window.__TEXTCLASH || [], str = v => v && typeof v === 'object' ? String(v.text ?? JSON.stringify(v)) : String(v ?? '');
  for (let i = Math.max(0, TC.length - 64); i < TC.length; i++) {                // 每帧清空或一直累加都行：只看最后 64 条，去重
    const x = TC[i] || {}, a = str(x.a), b = str(x.b), k = (x.shot || '') + '|' + a + '|' + b;
    if (!K.clash.has(k)) K.clash.set(k, { shot: x.shot || null, t: typeof x.t === 'number' ? x.t : t, seen: t, a, b });
  }
  if (!q) return [null, rec];
  let src = c;
  if (s !== 1) { const o = window.__SNAPCV || (window.__SNAPCV = document.createElement('canvas')), w = Math.round(c.width * s), h = Math.round(c.height * s);
    if (o.width !== w || o.height !== h) { o.width = w; o.height = h; }
    o.getContext('2d', { alpha: false }).drawImage(c, 0, 0, w, h); src = o; }
  return [src.toDataURL('image/jpeg', q / 100), rec];
}"""
# 取出并清空这一段记下的字、画面事件、放不下的文字块、同框文字冲突和运动模糊统计（每段开始前清空，分段复用时记录和视频对得上）。
# window.__MBSTAT = {frames, samples_total, max_used, draws_total} 由引擎累加；这里读完原地清零（引擎拿着这个对象的引用）。
TRACK_FLUSH_JS = r"""() => { const K = window.__TK, M = window.__MBSTAT;
  const out = { texts: [...K.texts].map(([k, v]) => { const i = k.indexOf('\u0001'); return [k.slice(0, i) || null, k.slice(i + 1), v[0], v[1]]; }),
                acts: [...K.acts.values()], fits: [...K.fits.values()], clash: [...K.clash.values()], overlaps: [...K.ovl.values()],
                mbstat: M ? { frames: +M.frames || 0, samples_total: +M.samples_total || 0, max_used: +M.max_used || 0, draws_total: +M.draws_total || 0 } : null };
  if (M) { M.frames = 0; M.samples_total = 0; M.max_used = 0; if ('draws_total' in M) M.draws_total = 0; }
  K.texts.clear(); K.acts.clear(); K.fits.clear(); K.clash.clear(); K.ovl.clear(); return out; }"""


TIME_HELP = '@ 后是镜头时长的比例（0~1）；镜头内秒数写 S02+1.2；绝对时刻直接写秒（12.5）或拍号（b12）'


def resolve_time(tl, x):
    """'S02@0.5' = 镜头 S02 的 50% 处；'S02+1.2' = 镜头 S02 开始后 1.2 秒；'b12' = 第 12 拍；'12.5' = 12.5 秒"""
    x = str(x)
    def scene(sid):
        if sid not in tl['scenes']:
            sys.exit(f'时间轴里没有镜头 {sid}。可选：{", ".join(tl["scenes"])}')
        return tl['scenes'][sid]
    if '@' in x:
        sid, f = x.split('@'); s = scene(sid)
        try: f = float(f)
        except ValueError: sys.exit(f'看不懂 {x}。{TIME_HELP}')
        if not 0 <= f <= 1:
            sys.exit(f'{x}：{TIME_HELP}。')
        return s['t0'] + min(f, 0.999) * s['dur']
    if '+' in x and not x[0].isdigit():
        sid, d = x.split('+', 1); s = scene(sid)
        try: return s['t0'] + float(d)
        except ValueError: sys.exit(f'看不懂 {x}。{TIME_HELP}')
    if x.startswith('b'):
        return tl.get('offset', 0) + float(x[1:]) * tl['beat']
    try: return float(x)
    except ValueError: sys.exit(f'看不懂 {x}。{TIME_HELP}')
