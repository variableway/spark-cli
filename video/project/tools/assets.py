"""素材工具：从网上拿真实产品的截图、logo、品牌色、图片，把视频拆成序列帧，整理成总览。
  python3 tools/assets.py shot <url> [名字]            首屏截图 + 整页长图（自动清弹窗、触发懒加载）→ web/img/<名字>.jpg、<名字>_full.jpg
  python3 tools/assets.py zoom <url> <名字> <选择器或 text=文字> [...]   同上，并把每个目标元素单独按 3 倍像素比截高清图 → <名字>_z1.png…，打印它在底图里的位置
  python3 tools/assets.py brand <url> [名字]           logo、图形标记（透明底）、品牌色、字体 → <名字>_logo.png、<名字>_mark.png、assets/brand.json，打印可粘进 project.json 的片段
  python3 tools/assets.py images <url> [名字]          下载页面里引用的大图（img、srcset、背景图、og:image）→ assets/raw/，最大的 12 张放进 web/img/
  python3 tools/assets.py frames <视频> [名字]          视频拆成序列帧 web/img/<名字>/0001.jpg…（SEQ.名字）
  python3 tools/assets.py prep <图片> [名字]            缩放、去纯色底（--key）、裁掉透明边（--trim）、调亮度和对比（--exposure 1.4），放进 web/img/
  python3 tools/assets.py sheet                        web/img/ 全部素材的总览 → frames/_view/assets_sheet.jpg
通用选项（shot/zoom/brand/images）：--width 1440 --height 900 --dpr 2 --mobile（390×844）--dark --wait 秒
  --hide "选择器"（重复）清不掉的遮挡直接隐藏   --click "按钮文字"（重复）先点掉   --timeout 秒（默认 120）总时限，超时杀 Chrome 退出
参考视频拆解（切点、节奏总览、BPM）用 tools/refsheet.py。
每次运行往 assets/manifest.json 追加一条（来源 URL、时间、文件、尺寸），交付时据此说明素材来源。
"""
import sys, os, re, json, time, base64, argparse, hashlib, subprocess, tempfile, contextlib, shutil, threading
from urllib.parse import urlparse, urljoin, unquote, parse_qs
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from common import ROOT, ffmpeg

RAW = ROOT / 'assets' / 'raw'
IMGDIR = ROOT / 'web' / 'img'
VIEW = ROOT / 'frames' / '_view'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
UA_M = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
ALT = '可换的来源：产品官网的 press / media kit 页、App Store / Google Play 商店截图、官方博客和 changelog 里的配图、官方 GitHub 仓库的 docs 与 README 图片。'
BLOCK_RE = re.compile(r'access denied|captcha|verify you are human|just a moment|attention required|are you a robot|unusual traffic|403 forbidden|enable javascript and cookies|请完成安全验证', re.I)


def warn(m): print('⚠️ ', m)


def slug(s, n=28):
    s = re.sub(r'[^a-z0-9]+', '-', unquote(s).lower()).strip('-')
    return s[:n].strip('-') or 'img'


def default_name(url):
    h = (urlparse(url).netloc or url).split(':')[0].split('.')
    h = [x for x in h if x not in ('www', 'app', 'm')]
    return slug(h[-2] if len(h) >= 2 else h[0] if h else 'site')


def rel(p): return str(Path(p).resolve().relative_to(ROOT))


def manifest(cmd, source, files, **extra):
    """追加一条素材来源记录。files: [路径]，自动补宽高。"""
    mp = ROOT / 'assets' / 'manifest.json'
    data = json.load(open(mp, encoding='utf-8')) if mp.exists() else []
    fl = []
    for f in files:
        d = {'file': rel(f)}
        try:
            with Image.open(f) as im: d['size'] = [im.width, im.height]
        except Exception:
            pass
        fl.append(d)
    data.append({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'cmd': cmd, 'source': source, 'files': fl, **extra})
    mp.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def save_web(im, name, alpha=None, long_max=4096, q=92):
    """存进 web/img/：有透明通道用 PNG，否则 JPEG。长边超过 long_max 才缩小。返回路径。"""
    IMGDIR.mkdir(parents=True, exist_ok=True)
    if max(im.size) > long_max:
        s = long_max / max(im.size); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    has_a = im.mode in ('RGBA', 'LA') and np.asarray(im.convert('RGBA'))[..., 3].min() < 250 if alpha is None else alpha
    for e in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'):         # 同名不同扩展名会让 IMG.名字 指向不确定，先清掉旧的
        if (IMGDIR / f'{name}{e}').exists(): (IMGDIR / f'{name}{e}').unlink()
    if has_a:
        p = IMGDIR / f'{name}.png'; im.convert('RGBA').save(p, optimize=True)
    else:
        p = IMGDIR / f'{name}.jpg'; im.convert('RGB').save(p, quality=q)
    return p


def blank_check(im, label):
    """几乎纯色的截图多半是白屏、被拦截或没加载出来。返回 True 表示有问题。"""
    a = np.asarray(im.convert('L').resize((96, 54)))
    top = np.bincount((a // 8).ravel()).max() / a.size
    if a.std() < 4 or top > 0.985:
        warn(f'{label} 几乎是纯色（标准差 {a.std():.1f}），可能白屏、被反爬或需要登录。加 --wait 8 再试，或换来源。\n   ' + ALT)
        return True
    return False


# ---------------------------------------------------------------- 浏览器
# 整机同时开很多 Chrome 时，Playwright 的 close / stop 会卡住不返回（产物已写盘，进程空转几分钟）。
# 两道保险：1) 总时限看门狗线程，到点按临时目录杀 Chrome、打印卡在哪一步和已写盘的产物后退出；
#          2) 关闭浏览器不走 Playwright 的 close：产物写盘后直接按临时目录杀 Chrome，立即继续。
# 线程里只做杀进程，不碰 Playwright（同步 API 不是线程安全的）。
LAUNCH_WAIT, LAUNCH_TRIES = 35, 3
_PHASE = ['启动']
_LIVE = set()
_PW = []


def phase(s): _PHASE[0] = s


def kill_chrome(udir):
    import psutil
    owned = []
    for process in psutil.process_iter(['cmdline']):
        try:
            args = process.info.get('cmdline') or []
            if '--user-data-dir=' + udir in args:
                owned.append(process)
                process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _, alive = psutil.wait_procs(owned, timeout=3)
    for process in alive:
        try: process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    shutil.rmtree(udir, ignore_errors=True)


def written_since(t0):
    out = []
    for d in (IMGDIR, RAW, ROOT / 'assets'):
        if d.exists():
            out += [rel(f) for f in sorted(d.iterdir()) if f.is_file() and f.stat().st_mtime >= t0 - 1 and f.name != 'manifest.json']
    return out


def _watchdog(t0, dl, done):
    """dl[0] 是截止时刻（可被延后）。到点还没 done：打印状态、杀 Chrome、退出进程。"""
    while not done.wait(0.5):
        if time.time() < dl[0]: continue
        files = written_since(t0)
        print(f'\n⏱ 超过 {dl[1]:g} 秒总时限，已强制退出。卡在：{_PHASE[0]}。', flush=True)
        print('   已写盘的产物：' + (('、'.join(files[:12]) + (f' 等 {len(files)} 个' if len(files) > 12 else '')) if files else '（无）'), flush=True)
        print(f'   处理：产物齐全就直接用；不齐全加 --timeout {int(dl[1] * 2)} 重试，或加 --wait 减少等待。整机同时开的 Chrome 很多时，错开运行。', flush=True)
        for u in list(_LIVE): kill_chrome(u)
        os._exit(3)


@contextlib.contextmanager
def browse(w=1440, h=900, dpr=2, dark=False, mobile=False, timeout=120):
    """本机 Chrome（独立临时用户目录，用完按目录杀掉），不带自动化特征的 UA。timeout：整个浏览器阶段的总时限（秒）。"""
    from playwright.sync_api import sync_playwright
    t0 = time.time(); dl = [t0 + timeout, timeout]; done = threading.Event(); threading.Thread(target=_watchdog, args=(t0, dl, done), daemon=True).start()
    phase('启动 Playwright')
    if not _PW: _PW.append(sync_playwright().start())             # 进程内只启动一次，不调用 stop()（stop 会卡）；命令结束由 main() 直接退出进程
    udir = None; ctx = None
    kw = dict(user_agent=UA_M if mobile else UA, is_mobile=mobile, has_touch=mobile) if mobile else dict(user_agent=UA)
    try:
        for attempt in range(LAUNCH_TRIES):                           # 整机 Chrome 很多时，启动可能卡住：等 LAUNCH_WAIT 秒还没起来就杀掉重来（杀进程会让卡住的调用报错返回）
            phase('启动 Chrome' + (f'（第 {attempt + 1} 次）' if attempt else ''))
            udir = tempfile.mkdtemp(prefix='mvs_chrome_'); _LIVE.add(udir)
            killer = threading.Timer(LAUNCH_WAIT, kill_chrome, [udir]); killer.start()
            try:
                ctx = _PW[0].chromium.launch_persistent_context(
                    udir, channel='chrome', headless=True, locale='en-US', viewport={'width': w, 'height': h}, device_scale_factor=dpr,
                    color_scheme='dark' if dark else 'light',
                    args=['--force-color-profile=srgb', '--hide-scrollbars', '--disable-blink-features=AutomationControlled'], **kw)
                killer.cancel(); break
            except Exception as e:
                killer.cancel(); kill_chrome(udir); _LIVE.discard(udir)
                print(f'   Chrome 启动失败或超时（{str(e)[:60]}），重试 {attempt + 1}/{LAUNCH_TRIES}', flush=True)
                if attempt == LAUNCH_TRIES - 1: raise
        phase('运行中')
        yield ctx
    finally:
        # 不调用 ctx.close()：整机 Chrome 多时它会卡住。用的是一次性临时用户目录，没有需要刷盘的数据，直接按目录杀进程。
        phase('关闭浏览器')
        if udir: kill_chrome(udir); _LIVE.discard(udir)
        done.set()


# 找出遮挡画面的东西：Cookie 横幅、订阅/登录弹窗、聊天浮窗。先点按钮，点不掉的由 hide 隐藏。
JS_OVERLAY = r"""
([mode, extraHide, extraClick]) => {
  const vw = innerWidth, vh = innerHeight, out = [];
  const NAME = /cookie|consent|gdpr|onetrust|cc-window|cmp|privacy|modal|dialog|popup|pop-up|newsletter|subscribe|signup|sign-up|overlay|backdrop|lightbox|intercom|drift|crisp|hubspot|zendesk|tidio|livechat|chat-?widget|launcher|beacon|promo-?bar|announcement/i;
  const COOKIE_TXT = /cookie|consent|privacy|gdpr|accept all|同意|隐私/i;
  const CLICK = /^(accept( all)?( cookies)?|allow( all)?( cookies)?|agree|i agree|got it|i understand|understood|no,? thanks?|not now|maybe later|dismiss|close|reject( all)?|decline|skip|skip for now|continue without .*|同意|接受|全部接受|我知道了|知道了|关闭|以后再说|暂不|不用了|拒绝)[\s.!×✕✖xX]*$/i;
  const desc = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
  const visible = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 4 && r.height > 4 && s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05; };
  const attrs = e => (e.id || '') + ' ' + (typeof e.className === 'string' ? e.className : '') + ' ' + (e.getAttribute('role') || '') + ' ' + (e.getAttribute('aria-label') || '') + ' ' + (e.getAttribute('aria-modal') || '');
  const all = [...document.querySelectorAll('body *')];
  const isOver = e => {
    const s = getComputedStyle(e); if (s.position !== 'fixed' || !visible(e)) return false;
    if (e.matches('main, header, nav, #root, #__next, #app') || e.querySelector('main')) return false;
    const r = e.getBoundingClientRect(), area = r.width * r.height / (vw * vh);
    const topBar = r.top <= 2 && r.height < 120 && r.width > vw * .8 && !/cookie|consent|banner|promo|announcement/i.test(attrs(e));
    if (topBar) return false;
    if (e.tagName === 'IFRAME') return r.width < vw * .6;
    if (e.matches('[role=dialog],[role=alertdialog],[aria-modal=true],dialog')) return true;
    if (NAME.test(attrs(e)) && !/^(nav|navbar|header|sidebar)/i.test(e.id)) return true;
    const kids = e.querySelectorAll('*').length;
    if (area < .4 && /cookie|consent|gdpr|accept all|reject all|同意|隐私政策/i.test(e.textContent.slice(0, 500)) && e.querySelector('button, a, [role=button]')) return true;   // 角落里的 Cookie 小卡片
    if (area > .6 && kids <= 3 && s.backgroundColor !== 'rgba(0, 0, 0, 0)') return true;                    // 半透明遮罩
    if (r.bottom >= vh - 4 && r.height < 280 && r.width > vw * .5 && COOKIE_TXT.test(e.textContent.slice(0, 600))) return true;   // 底部 Cookie 条
    return false;
  };
  const hosts = [...document.querySelectorAll('*')].filter(e => e.shadowRoot && e.style.display !== 'none' && NAME.test(attrs(e)));            // Shadow DOM 里的同意管理器（Transcend、Usercentrics 等），宿主本身尺寸为 0
  const over = all.filter(isOver).filter((e, _, a) => !a.some(o => o !== e && o.contains(e)));          // 只留最外层
  if (mode === 'click') {
    const clicked = [];
    const tryBtn = root => {
      const bs = [...root.querySelectorAll('button, a, [role=button], input[type=button], input[type=submit]')].filter(visible);
      let b = bs.find(x => CLICK.test((x.innerText || x.value || '').trim()) && !/^(accept|agree)$/i.test('') );
      if (!b) b = bs.find(x => /close|dismiss|关闭/i.test((x.getAttribute('aria-label') || '') + (x.title || '')));
      if (!b) b = bs.find(x => /^[×✕✖xX]$/.test((x.innerText || '').trim()));
      if (b) { b.click(); clicked.push(desc(b) + ' 「' + (b.innerText || b.getAttribute('aria-label') || '').trim().slice(0, 20) + '」'); return true; }
      return false;
    };
    for (const root of over) tryBtn(root);
    for (const h of hosts) tryBtn(h.shadowRoot);
    if (over.length && !clicked.length) {                      // 有弹窗但没找到带字的关闭按钮：点右上角的纯图标按钮（常见的 × 只有一个 svg）
      const ic = [...document.querySelectorAll('button, [role=button]')].filter(b => { const r = b.getBoundingClientRect(); return visible(b) && !(b.innerText || '').trim() && b.querySelector('svg') && r.width < 64 && r.height < 64 && r.top < 160 && r.right > vw - 220 && getComputedStyle(b).position === 'fixed' || (visible(b) && !(b.innerText || '').trim() && b.querySelector('svg') && r.width < 64 && r.top < 120 && r.right > vw - 120 && over.some(o => o.contains(b))); });
      if (ic[0]) { ic[0].click(); clicked.push(desc(ic[0]) + ' 「右上角图标」'); }
    }
    const fixed = ['#onetrust-accept-btn-handler', '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', '.cc-allow', '.cc-dismiss', '[data-testid=cookie-accept]', '#truste-consent-button', 'button[aria-label="Close"]'];
    for (const sel of fixed) { const b = document.querySelector(sel); if (b && visible(b)) { b.click(); clicked.push(sel); } }
    for (const t of extraClick) { const b = [...document.querySelectorAll('button, a, [role=button]')].find(x => visible(x) && (x.innerText || '').trim().toLowerCase() === t.toLowerCase()); if (b) { b.click(); clicked.push('「' + t + '」'); } }
    return clicked;
  }
  const hidden = [];
  for (const h of hosts) { h.style.setProperty('display', 'none', 'important'); hidden.push(desc(h) + '（Shadow DOM）'); }
  for (const e of over) {
    const r = e.getBoundingClientRect(), back = r.width * r.height / (vw * vh) > .6 && e.querySelectorAll('*').length <= 3;
    e.style.setProperty('display', 'none', 'important'); hidden.push(desc(e));
    if (back) for (let n = e.nextElementSibling; n; n = n.nextElementSibling) if (getComputedStyle(n).position === 'fixed' && visible(n)) { n.style.setProperty('display', 'none', 'important'); hidden.push(desc(n) + '（遮罩后面的弹窗内容）'); }   // 遮罩的同级 fixed 节点就是弹窗本体
  }
  for (const sel of extraHide) document.querySelectorAll(sel).forEach(e => { e.style.setProperty('display', 'none', 'important'); hidden.push(sel); });
  if (hidden.length) for (const e of [document.documentElement, document.body]) { if (getComputedStyle(e).overflow === 'hidden') e.style.setProperty('overflow', 'auto', 'important'); }
  return hidden;
}
"""


def dismiss(pg, hide=(), click=(), rounds=2):
    """先点 Cookie/弹窗按钮，点不掉就隐藏。返回处理记录。"""
    log = []
    for _ in range(rounds):
        c = pg.evaluate(JS_OVERLAY, ['click', [], list(click)])
        if c: log += ['点击 ' + x for x in c]; pg.wait_for_timeout(900)
        h = pg.evaluate(JS_OVERLAY, ['hide', list(hide), []])
        if h: log += ['隐藏 ' + x for x in h]; pg.wait_for_timeout(300)
        if not c and not h: break
    return log


# 找真正在滚动的元素：很多单页应用 body 不滚动，内容在内部容器（甚至浮层）里。document 不够长时找 scrollHeight 最大的 overflow:auto/scroll 元素。
JS_SCROLLER = r"""
() => {
  document.querySelectorAll('[data-mvs-scroller]').forEach(e => e.removeAttribute('data-mvs-scroller'));
  const vw = innerWidth, vh = innerHeight, de = document.documentElement;
  let best = null, bh = de.scrollHeight > vh * 1.15 ? de.scrollHeight : 0;
  for (const e of document.querySelectorAll('body *')) {
    if (e.scrollHeight < Math.max(e.clientHeight * 1.3, vh * 1.2) || e.scrollHeight <= bh) continue;
    if (!/(auto|scroll|overlay)/.test(getComputedStyle(e).overflowY)) continue;
    const r = e.getBoundingClientRect(); if (r.width < vw * .4 || r.height < vh * .5) continue;
    best = e; bh = e.scrollHeight;
  }
  if (best) best.setAttribute('data-mvs-scroller', '1');
  return { kind: best ? 'inner' : 'doc', h: bh || de.scrollHeight };
}
"""
JS_ALIVE = r"""() => { const e = document.querySelector('[data-mvs-scroller]'); if (!e || !e.isConnected) return false; const r = e.getBoundingClientRect(); return r.width > 50 && r.height > 50 && getComputedStyle(e).visibility !== 'hidden' && e.scrollHeight > e.clientHeight * 1.3; }"""
JS_RECT = r"""e => { const r = e.getBoundingClientRect(), sc = document.querySelector('[data-mvs-scroller]'), inS = !!sc && sc !== e && sc.contains(e); let cx, cy;
  if (inS) { const c = sc.getBoundingClientRect(); cx = r.left - c.left; cy = r.top - c.top + sc.scrollTop; } else { cx = r.left + scrollX; cy = r.top + scrollY; }
  return { x: r.left, y: r.top, w: r.width, h: r.height, cx, cy, inS, vw: innerWidth, vh: innerHeight }; }"""


def scroll_to(pg, kind, y):
    return pg.evaluate("([k,y])=>{const e=k==='inner'?document.querySelector('[data-mvs-scroller]'):document.scrollingElement;if(!e)return null;e.scrollTo(0,y);return [e.scrollTop,e.scrollHeight,e.clientHeight]}", [kind, y])


def scroll_through(pg, kind):
    """从上到下滚一遍（按滚动元素自己的高度，每次 0.8 屏），触发懒加载和进场动画，再回顶。"""
    y = 0
    for _ in range(80):
        r = scroll_to(pg, kind, y)
        if not r: break
        pg.wait_for_timeout(250)
        if y >= r[1] - r[2] or y > 40000: break
        y += max(200, int(r[2] * .8))
    pg.wait_for_timeout(500)
    try: pg.wait_for_load_state('networkidle', timeout=4000)
    except Exception: pass
    scroll_to(pg, kind, 0); pg.wait_for_timeout(500)


def stitch(pg, a):
    """内部滚动容器的长图：分段滚动截图再拼接（sticky/fixed 的页头只留第一段）。返回 (PIL 图, [L,T,宽,可视高,总高,截取高])。"""
    L, T, Wc, Ch, Sh = pg.evaluate("()=>{const e=document.querySelector('[data-mvs-scroller]');const r=e.getBoundingClientRect();return [r.left,r.top,r.width,e.clientHeight,e.scrollHeight]}")
    H = min(Sh, int(a.full_max))
    if Sh > H: print(f'   内部容器高 {Sh}px，截断到 {H}px（--full-max 可调）')
    base = min(a.dpr, 2); k = base / a.cdpr
    out = Image.new('RGB', (round(Wc * base), round(H * base)), (255, 255, 255)); y = 0; tmp = RAW / '_strip.png'
    for i in range(200):
        r = scroll_to(pg, 'inner', y); pg.wait_for_timeout(220)
        st = r[0]
        if i == 1: pg.evaluate("()=>{const c=document.querySelector('[data-mvs-scroller]');window.__mvsHid=[...c.querySelectorAll('*')].filter(e=>/^(sticky|fixed)$/.test(getComputedStyle(e).position));window.__mvsHid.forEach(e=>e.style.setProperty('visibility','hidden','important'))}")
        pg.screenshot(path=str(tmp), clip={'x': L, 'y': T, 'width': Wc, 'height': Ch})
        im = Image.open(tmp).convert('RGB')
        if k != 1: im = im.resize((round(Wc * base), round(Ch * base)), Image.LANCZOS)
        off = round((y - st) * base)
        out.paste(im.crop((0, off, im.width, im.height)), (0, round(y * base)))
        if st + Ch <= y: break
        y = st + Ch
        if y >= H: break
    pg.evaluate("()=>{(window.__mvsHid||[]).forEach(e=>e.style.removeProperty('visibility'))}")
    scroll_to(pg, 'inner', 0); tmp.unlink(missing_ok=True)
    return out, [L, T, Wc, Ch, Sh, H]


def open_site(ctx, url, a, hook=None):
    """打开页面：等 load、网络空闲、字体就绪；找到真正滚动的元素，从头滚到底触发懒加载并收集图片；
    hook(pg, S) 在清弹窗之前调用（内容在浮层里时，关掉弹窗内容就没了）；再清弹窗。
    返回 (page, notes, 弹窗记录)；page 上挂着 pg.S（滚动元素）、pg.imgs（图片清单）、pg.alive（清弹窗后滚动容器还在）、pg.S2（清弹窗后的滚动元素）。"""
    pg = ctx.new_page(); notes = []; fonts = []
    pg.on('response', lambda r: fonts.append(r.url) if re.search(r'\.(woff2?|ttf|otf)(\?|$)', r.url) else None)
    pg.fonts = fonts; pg.imgs = []; pg.alive = False
    status = None; phase('打开页面')
    try:
        r = pg.goto(url, wait_until='domcontentloaded', timeout=45000); status = r.status if r else None
    except Exception as e:
        notes.append(f'打开超时或失败：{str(e)[:120]}')
    for st, to in (('load', 20000), ('networkidle', 12000)):
        try: pg.wait_for_load_state(st, timeout=to)
        except Exception: pass
    try: pg.evaluate('document.fonts.ready')
    except Exception: pass
    phase('等待页面稳定'); pg.wait_for_timeout(int(a.wait * 1000))
    log = []
    try:
        pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
        S = pg.S = pg.evaluate(JS_SCROLLER)
        if S['kind'] == 'inner': print(f'   页面主体在内部滚动容器里（高 {S["h"]}px，视口 {a.height}px），按容器滚动和截长图；它可能是个浮层，会在关闭弹窗前先截。')
        phase('滚动页面触发懒加载'); scroll_through(pg, S['kind'])
        pg.imgs = pg.evaluate(JS_IMAGES)
        if hook: hook(pg, S)
        phase('清理弹窗'); log = dismiss(pg, a.hide, a.click)
        scroll_to(pg, 'doc', 0); pg.wait_for_timeout(400)
        log += dismiss(pg, a.hide, a.click)
        try: pg.wait_for_load_state('networkidle', timeout=5000)
        except Exception: pass
        pg.alive = S['kind'] == 'inner' and pg.evaluate(JS_ALIVE)
        pg.S2 = S if pg.alive else pg.evaluate(JS_SCROLLER)
        if pg.S2['kind'] == 'inner' and not pg.alive: scroll_through(pg, 'inner')       # 关掉浮层后露出另一个滚动容器
    except Exception as e:
        notes.append(f'滚动或清弹窗失败：{str(e)[:80]}'); pg.S2 = getattr(pg, 'S2', {'kind': 'doc', 'h': a.height})
    try: body = pg.evaluate('(document.title||"")+" | "+document.body.innerText.slice(0,500)')
    except Exception: body = ''
    if status and status >= 400: notes.append(f'HTTP {status}')
    if BLOCK_RE.search(body[:600]): notes.append('页面像是反爬或验证页：' + body[:80].replace('\n', ' '))
    pu, uu = urlparse(pg.url), urlparse(url)
    if re.search(r'login|signin|sign-in|sign_in|accounts?\.', pu.path + pu.netloc, re.I) and not re.search(r'login|signin|sign-in', uu.path, re.I):
        notes.append(f'被跳转到登录页：{pg.url}')
    if pu.netloc != uu.netloc: notes.append(f'域名被重定向：{pg.url}')
    if notes: warn('；'.join(notes) + '\n   ' + ALT)
    return pg, notes, log


def save_shot(im, nm, files, a):
    bad = blank_check(im, nm)
    p = save_web(im, nm, alpha=False, long_max=12000); files.append(p)
    print(f'✓ {rel(p)}  {im.width}×{im.height}')
    return bad


def do_shot(ctx, url, name, a, zooms=()):
    RAW.mkdir(parents=True, exist_ok=True)
    files, results, bad = [], {}, False
    st = {}

    def inside(pg, sel):
        try:
            loc = pg.locator(sel)
            return loc.count() > 0 and loc.first.evaluate("e=>{const s=document.querySelector('[data-mvs-scroller]');return !!s&&s!==e&&s.contains(e)}")
        except Exception:
            return False

    def hook(pg, S):                                 # 滚动容器可能是浮层：关弹窗之前先截长图，并把在容器里的目标先截好
        if S['kind'] != 'inner': return
        st['pre'] = stitch(pg, a); st['texts'] = pg.evaluate(JS_TEXTS)       # 关弹窗前的页面文字，找不到目标时给「相近文字」用
        for i, sel in enumerate(zooms):
            if inside(pg, sel):
                r = do_zoom(pg, sel, zname(i), a, st['pre'][1], None)
                if r: r['pre'] = True; results[i] = r
        scroll_to(pg, 'inner', 0)

    def zname(i): return f'{name}_z{i + 1}' if not a.tag else f'{name}_{a.tag.split(",")[i]}'
    pg, notes, log = open_site(ctx, url, a, hook)
    print('弹窗处理：' + ('；'.join(log) if log else '没发现遮挡'))
    top = RAW / f'{name}_top.png'; pg.screenshot(path=str(top))
    im = Image.open(top).convert('RGB')
    if a.cdpr > min(a.dpr, 2): im = im.resize((round(im.width * min(a.dpr, 2) / a.cdpr), round(im.height * min(a.dpr, 2) / a.cdpr)), Image.LANCZOS)
    bad |= save_shot(im, name, files, a)
    # 整页长图：优先用清弹窗之后的页面；浮层里的内容（关闭前截的）单独保存
    S2, pre = pg.S2, st.get('pre'); long_box = None; sc_name = name + '_full'; pre_name = None
    cap = min(int(a.full_max), int(15000 / a.cdpr))
    if pg.alive:                                       # 滚动容器还在：没有弹窗干扰就沿用关闭前截的
        pre_name = sc_name
        if pre and not log: im, long_box = pre
        else: im, long_box = stitch(pg, a)
        bad |= save_shot(im, sc_name, files, a)
    else:
        if S2['kind'] == 'inner':
            im, long_box = stitch(pg, a); bad |= save_shot(im, sc_name, files, a)
            if pre: pre_name = name + '_overlay_full'
        elif S2['h'] > a.height * 1.05:
            H = min(S2['h'], cap)
            if S2['h'] > cap: print(f'   整页高 {S2["h"]}px，截断到 {cap}px（--full-max 可调）')
            fp = RAW / f'{name}_full.png'; pg.screenshot(path=str(fp), full_page=True, clip={'x': 0, 'y': 0, 'width': a.width, 'height': H})
            im = Image.open(fp).convert('RGB')
            if a.cdpr > min(a.dpr, 2): im = im.resize((round(im.width * min(a.dpr, 2) / a.cdpr), round(im.height * min(a.dpr, 2) / a.cdpr)), Image.LANCZOS)
            bad |= save_shot(im, sc_name, files, a); fp.unlink()
            if pre: pre_name = name + '_overlay_full'
        else:
            sc_name = None; print('   页面没有比首屏更长，不保存整页长图。')
            if pre: pre_name = name + '_full'
        if pre:
            bad |= save_shot(pre[0], pre_name, files, a)
            print(f'   {pre_name} 是关闭弹窗之前截的：页面主体内容在浮层里，关掉后看到的是浮层后面的页面（{name}）。')
    # 剩下的目标：关弹窗之后的页面里找
    for i, sel in enumerate(zooms):
        if i in results: continue
        r = do_zoom(pg, sel, zname(i), a, long_box, S2['h'] if S2['kind'] == 'doc' and S2['h'] > a.height * 1.05 else None, st.get('texts', ()))
        if r: results[i] = r
    out = []
    for i in sorted(results):
        r = results[i]; files.append(r['path'])
        if r['inS']:                                    # 在滚动容器里：位置相对长图；首屏底图只有容器没被关掉时才对得上
            r['base_full'] = pre_name if (r.get('pre') and pre_name) else sc_name
            if not (pg.alive and r['top']): r['top'] = None
        else:
            r['base_full'] = sc_name if r['full'] else None
        report_zoom(r, name)
        out.append({k: v for k, v in r.items() if k not in ('path', 'pre')})
    pg.close()
    manifest('zoom' if zooms else 'shot', url, files + [top], notes=notes, popups=log, dark=a.dark, zooms=out or None)
    return not bad


JS_TEXTS = r"""()=>{const o=new Set();document.querySelectorAll('body *').forEach(e=>{const t=[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ').trim();if(t&&t.length<90)o.add(t)});return [...o].slice(0,3000)}"""


def zoom_diag(pg, sel, err, extra=()):
    """找不到或超时：说清候选数量、页面上相近的文字，并给出出路。"""
    try: n = pg.locator(sel).count()
    except Exception as e: n = -1; err = e
    print(f'⚠️  zoom 目标 {sel!r} 失败：' + (f'选择器语法错误（{str(err)[:60]}）' if n < 0 else f'匹配到 {n} 个元素' + ('，选择器没有命中' if n == 0 else '，但等不到它可见或加载完（被遮挡、display:none、还没渲染）')))
    m = re.findall(r"""(?:text=|has-text\(|text\()["']?([^"')]+)""", sel); needle = (m[0] if m else sel).strip().lower()
    try:
        texts = list(dict.fromkeys(list(extra) + pg.evaluate(JS_TEXTS)))
        import difflib
        low = {t.lower(): t for t in texts}
        close = difflib.get_close_matches(needle, list(low), n=5, cutoff=.35)
        close += [low[k] for k in low if needle[:6] and needle[:6] in k and low[k] not in close][:3]
        if close: print('   页面上相近的文字：' + ' | '.join(dict.fromkeys(low.get(c, c) for c in close)))
        else: print(f'   页面上没有相近的文字（共 {len(texts)} 段文字）。目标可能还没加载，加 --wait 8，或在内部滚动容器外。')
    except Exception:
        pass
    print('   出路：(1) 改用更准的选择器或 text=；(2) 内容是懒加载的功能图时，直接用 images 下载原图，比截图更清楚；(3) --hide / --click 先处理遮挡。')


def do_zoom(pg, sel, out, a, box, doc_h, extra=()):
    """单独截一个元素的高清图（--zdpr 倍，默认 3）：先滚到视口中间、等里面的图片加载完再截，并算出它在底图里的归一化矩形。
    box：滚动容器长图的 [L,T,宽,可视高,总高,截取高]（目标在容器里时用）；doc_h：普通页面整页高（>首屏时才有整页底图）。"""
    loc = pg.locator(sel).first
    try:
        loc.wait_for(state='attached', timeout=6000)
        loc.evaluate("e=>{for(const i of [e,...e.querySelectorAll('img')]) if(i.tagName==='IMG') i.loading='eager'; e.scrollIntoView({block:'center',inline:'nearest'})}")
        loc.evaluate("e=>Promise.race([Promise.all([e,...e.querySelectorAll('img')].filter(i=>i.tagName==='IMG').map(i=>i.complete&&i.naturalWidth?1:new Promise(r=>{i.onload=i.onerror=r}))),new Promise(r=>setTimeout(r,6000))])")
        pg.wait_for_timeout(400)
        m = loc.evaluate(JS_RECT)
    except Exception as e:
        zoom_diag(pg, sel, e, extra); return None
    pad = a.pad
    x0, y0 = max(0, m['x'] - pad), max(0, m['y'] - pad); x1, y1 = min(m['vw'], m['x'] + m['w'] + pad), min(m['vh'], m['y'] + m['h'] + pad)
    w, h = x1 - x0, y1 - y0
    if m['w'] < 4 or m['h'] < 4 or w < 4 or h < 4:
        warn(f'元素 {sel!r} 尺寸为 {m["w"]:.0f}×{m["h"]:.0f}，不可见（被隐藏或还没渲染）。'); return None
    if m['w'] + 2 * pad > m['vw'] + 1 or m['h'] + 2 * pad > m['vh'] + 1: warn(f'元素 {sel!r} 比视口还大（{m["w"]:.0f}×{m["h"]:.0f}），只截到可见部分。可加大 --width / --height，或换更小的子元素。')
    cx, cy = m['cx'] - (m['x'] - x0), m['cy'] - (m['y'] - y0)            # 实际截取区域在内容坐标里的左上角
    raw = RAW / f'{out}.png'
    pg.screenshot(path=str(raw), clip={'x': x0, 'y': y0, 'width': w, 'height': h})
    im = Image.open(raw).convert('RGB'); blank_check(im, out)
    p = IMGDIR / f'{out}.png'; IMGDIR.mkdir(parents=True, exist_ok=True); im.save(p, optimize=True)         # 高清局部存 PNG：推近到 3–4 倍时 JPEG 的压缩噪点会显出来
    full = top = None
    if m['inS'] and box:
        L, T, Wc, Ch, Sh, Hh = box
        if cy + h <= Hh + 1: full = [cx / Wc, cy / Hh, w / Wc, h / Hh]
        if cy + h <= Ch and T + cy + h <= a.height: top = [(L + cx) / a.width, (T + cy) / a.height, w / a.width, h / a.height]
    elif not m['inS']:
        if doc_h and cy + h <= doc_h + 1: full = [cx / a.width, cy / doc_h, w / a.width, h / doc_h]
        if cy + h <= a.height + 1: top = [cx / a.width, cy / a.height, w / a.width, h / a.height]
    rd = lambda v: [round(t, 5) for t in v] if v else None
    print(f'✓ {rel(p)}  {im.width}×{im.height}（{a.zdpr:g}×）  元素 CSS 矩形 x={cx:.0f} y={cy:.0f} w={w:.0f} h={h:.0f}' + ('（在内部滚动容器里）' if m['inS'] else ''))
    return {'path': p, 'selector': sel, 'out': out, 'inS': m['inS'], 'css_rect': [round(v, 1) for v in (cx, cy, w, h)], 'top': rd(top), 'full': rd(full), 'zdpr': a.zdpr}


def report_zoom(r, name):
    shown = False
    for key, base in (('top', name), ('full', r.get('base_full'))):
        v = r[key]
        if not v or not base: continue
        shown = True
        print(f'   在底图 {base} 里的归一化矩形 [x,y,w,h]={v}  →  GL3D.card sub=[{v[0]},{v[1]},{round(v[0] + v[2], 5)},{round(v[1] + v[3], 5)}]（底图用同样的 x/y/w/h 画，高清局部加 sub 再画一次）')
    if not shown: print(f'   {r["out"]} 超出了所有底图的范围（目标在长图被截断的部分，或在被关掉的浮层里）：只能单独当一张图用，或加大 --full-max。')


# ---------------------------------------------------------------- brand
JS_LOGO = r"""
() => {
  const NS = 'http://www.w3.org/2000/svg';
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 8 && r.height > 8 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const logoish = e => { for (let n = e, i = 0; n && i < 4; n = n.parentElement, i++) if (/logo|brand|wordmark/i.test((n.id || '') + ' ' + (typeof n.className === 'string' ? n.className : '') + ' ' + (n.getAttribute('aria-label') || '') + ' ' + (n.getAttribute('title') || ''))) return true; return false; };
  const homeLink = e => { const a = e.closest('a'); if (!a) return false; try { const u = new URL(a.href); return u.origin === location.origin && (u.pathname === '/' || u.pathname === location.pathname); } catch (_) { return false; } };
  const score = e => { const r = e.getBoundingClientRect(); let s = 0;
    if (homeLink(e)) s += 3; if (logoish(e)) s += 3; if (e.closest('header, nav, [class*=header], [class*=navbar]')) s += 2; if (r.top < 160) s += 1;
    if (e.tagName === 'svg' && e.closest('button') && !homeLink(e) && !logoish(e)) s -= 4; if (r.width < 24 && r.height < 24) s -= 2; if (r.width > 400) s -= 3; if (r.top > 600) s -= 4; return s; };
  const inl = (o, c) => {                                   // 把计算样式写进副本，脱离页面 CSS 也能渲染
    const s = getComputedStyle(o);
    if (c.nodeType === 1 && o.nodeType === 1) {
      const st = []; for (const k of ['fill', 'stroke', 'stroke-width', 'opacity', 'fill-opacity', 'stroke-opacity', 'fill-rule', 'stroke-linecap', 'stroke-linejoin', 'color', 'display', 'visibility']) st.push(k + ':' + s.getPropertyValue(k));
      c.setAttribute('style', st.join(';')); c.removeAttribute('class');
    }
  };
  const ser = svg => {
    const r = svg.getBoundingClientRect(), c = svg.cloneNode(true);
    const oa = [svg, ...svg.querySelectorAll('*')], ca = [c, ...c.querySelectorAll('*')];
    oa.forEach((o, i) => inl(o, ca[i]));
    ca.filter(x => x.tagName.toLowerCase() === 'use').forEach(u => {                // <use> 引用外部 symbol：把内容复制进来
      const id = (u.getAttribute('href') || u.getAttribute('xlink:href') || '').replace(/^.*#/, ''); const t = id && document.getElementById(id); if (!t) return;
      const g = document.createElementNS(NS, 'g'); const col = getComputedStyle(oa[ca.indexOf(u)]).fill;
      for (const k of (t.tagName.toLowerCase() === 'symbol' ? [...t.children] : [t])) { const kc = k.cloneNode(true); if (!kc.getAttribute('fill') || kc.getAttribute('fill') === 'currentColor') kc.setAttribute('fill', col); g.appendChild(kc); }
      u.replaceWith(g);
    });
    c.setAttribute('xmlns', NS); c.setAttribute('width', r.width); c.setAttribute('height', r.height);
    if (!c.getAttribute('viewBox')) c.setAttribute('viewBox', `0 0 ${r.width} ${r.height}`);
    return new XMLSerializer().serializeToString(c);
  };
  const out = [];
  document.querySelectorAll('svg').forEach(e => { if (!vis(e) || e.closest('svg') !== e) return; const sc = score(e); if (sc >= 2) out.push({ kind: 'svg', score: sc, w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height, svg: ser(e) }); });
  document.querySelectorAll('img').forEach(e => { if (!vis(e)) return; const sc = score(e) + (/logo/i.test((e.alt || '') + e.src) ? 2 : 0); if (sc >= 3) out.push({ kind: 'img', score: sc, w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height, src: e.currentSrc || e.src }); });
  out.sort((a, b) => b.score - a.score || b.w * b.h - a.w * a.h);
  // 页头里指向首页的链接（logo 一般在这里）：取里面全部 svg / img，用来提取图形标记
  const homeRe = /^\/([a-z]{2}([-_][a-z]{2,4})?)?\/?$|^\/(home|homepage|index)\/?$/i;      // /、/en、/zh-cn、/home、/homepage
  const isHome = a => { try { const u = new URL(a.href); return u.origin === location.origin && (homeRe.test(u.pathname) || u.pathname === location.pathname); } catch (_) { return false; } };
  const anchors = [...document.querySelectorAll('a')].filter(a => { const r = a.getBoundingClientRect(); return isHome(a) && r.top < 200 && r.width > 8 && r.height > 8 && a.querySelector('svg, img'); })
    .sort((a, b) => (!a.closest('header, nav') - !b.closest('header, nav')) || a.getBoundingClientRect().top - b.getBoundingClientRect().top || a.getBoundingClientRect().left - b.getBoundingClientRect().left);
  const homes = [];
  if (anchors[0]) anchors[0].querySelectorAll('svg, img').forEach(e => {
    if (e.parentElement.closest('svg') || !vis(e)) return; const r = e.getBoundingClientRect();
    homes.push(e.tagName.toLowerCase() === 'svg' ? { kind: 'svg', svg: ser(e), w: r.width, h: r.height, x: r.left, y: r.top } : { kind: 'img', src: e.currentSrc || e.src, w: r.width, h: r.height, x: r.left, y: r.top });
  });
  const links = [...document.querySelectorAll('link[rel*=icon], link[rel=mask-icon]')].map(l => ({ rel: l.rel, href: l.href, sizes: l.sizes ? l.sizes.value : '', type: l.type }));
  const meta = n => { const m = document.querySelector(`meta[property="${n}"], meta[name="${n}"]`); return m ? m.content : null; };
  return { cands: out.slice(0, 5), homes, links, og: meta('og:image') || meta('twitter:image'), theme: meta('theme-color'), title: document.title, site: meta('og:site_name') };
}
"""

JS_COLORS = r"""
() => {
  const cv = document.createElement('canvas').getContext('2d', { willReadFrequently: true }); cv.canvas.width = cv.canvas.height = 1;
  const rgb = v => { v = (v || '').trim(); if (!v) return null; if (/^[\d.]+\s+[\d.]+%\s+[\d.]+%/.test(v)) v = 'hsl(' + v + ')';
    cv.clearRect(0, 0, 1, 1); cv.fillStyle = '#010203'; cv.fillStyle = v; cv.fillRect(0, 0, 1, 1); const d = cv.getImageData(0, 0, 1, 1).data;
    if (d[3] < 200) return null; if (d[0] === 1 && d[1] === 2 && d[2] === 3 && v.replace(/\s/g, '') !== '#010203') return null; return [d[0], d[1], d[2]]; };
  const vars = {};
  const walk = rules => { for (const r of rules) { try { if (r.cssRules && !r.style) walk(r.cssRules); else if (r.style && /^(:root|html|body|\.dark|\.light|\[data-theme.*\])$/.test(r.selectorText || '')) for (const n of r.style) if (n.startsWith('--')) { const c = rgb(r.style.getPropertyValue(n)); if (c) vars[(r.selectorText.includes('dark') ? 'dark:' : '') + n] = c; } } catch (_) {} } };
  for (const s of document.styleSheets) { try { walk(s.cssRules); } catch (_) {} }
  const cs = e => getComputedStyle(e);
  const bgOf = e => { for (let n = e; n; n = n.parentElement) { const c = rgb(cs(n).backgroundColor); if (c) return c; } return [255, 255, 255]; };
  const btn = []; document.querySelectorAll('button, a[class*=btn], a[class*=button], a[class*=cta], [role=button], a[href*=signup], a[href*=get-started], a[href*=sign-up]').forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 40 || r.height < 20 || r.top > 1400) return; const c = rgb(cs(e).backgroundColor); if (c) btn.push(c); });
  const link = []; document.querySelectorAll('a').forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 10 || r.top > 1400) return; const c = rgb(cs(e).color); if (c) link.push(c); });
  const tx = {}, bgs = {}, vw = innerWidth, vh = innerHeight;                  // 饱和色按文字数量、背景按面积统计，比 CSS 变量更接近肉眼看到的主色
  document.querySelectorAll('body *').forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4 || r.top > 1400 || r.bottom < 0) return; const s = cs(e);
    const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('').length;
    if (own) { const c = rgb(s.color); if (c) tx[c] = (tx[c] || 0) + own; }
    const b = rgb(s.backgroundColor); if (b) { const ar = r.width * r.height / (vw * vh); if (ar < .5) bgs[b] = (bgs[b] || 0) + ar; } });
  const hd = document.querySelector('h1'), bd = document.body;
  const fam = e => e ? cs(e).fontFamily : '';
  const fonts = { h1: fam(hd), body: fam(document.querySelector('p') || bd), button: fam(document.querySelector('button')), code: fam(document.querySelector('code, pre')) };
  const loaded = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, ''));
  return { tx: Object.entries(tx).map(([k, v]) => [k.split(',').map(Number), v]), bgs: Object.entries(bgs).map(([k, v]) => [k.split(',').map(Number), v]), vars, btn, link, bodyBg: bgOf(bd), bodyInk: rgb(cs(bd).color), h1Ink: hd ? rgb(cs(hd).color) : null, themeColor: (document.querySelector('meta[name=theme-color]') || {}).content, fonts, loaded };
}
"""

GENERIC = {'segoe ui emoji', 'segoe ui symbol', 'noto color emoji', 'segoe ui', 'serif', 'sans-serif', 'monospace', 'system-ui', 'ui-sans-serif', 'ui-serif', 'ui-monospace', 'cursive', 'fantasy', 'ui-rounded', '-apple-system', 'blinkmacsystemfont', 'segoe ui', 'roboto', 'helvetica neue', 'helvetica', 'arial', 'apple color emoji', 'noto sans', 'oxygen', 'ubuntu', 'cantarell'}


def pick_font(stack):
    for f in [x.strip().strip('"\'') for x in (stack or '').split(',')]:
        m = re.match(r'^__(.+?)(_Fallback)?_[0-9a-f]{5,8}$', f)          # next/font 会把名字改成 __Inter_a1b2c3
        if m:
            if m.group(2): continue
            f = m.group(1).replace('_', ' ')
        if f and f.lower() not in GENERIC and not f.lower().endswith('fallback'): return f
    return None


def hexc(c): return '#%02X%02X%02X' % tuple(int(round(v)) for v in c)
def mix(a, b, t): return [a[i] * (1 - t) + b[i] * t for i in range(3)]
def sat(c): return (max(c) - min(c)) / 255
def hue_gap(a, b):
    import colorsys
    d = abs(colorsys.rgb_to_hsv(*[v / 255 for v in a])[0] - colorsys.rgb_to_hsv(*[v / 255 for v in b])[0]); return min(d, 1 - d)
def dist(a, b): return sum((a[i] - b[i]) ** 2 for i in range(3)) ** .5


def screenshot_colors(path, n=6):
    """首屏截图里面积最大的饱和色（饱和度 > 0.3 且不太暗），按面积占比排序。"""
    im = np.asarray(Image.open(path).convert('RGB').resize((200, 125))).reshape(-1, 3).astype(float)
    q = (im // 24 * 24 + 12).astype(int); keys, cnt = np.unique(q, axis=0, return_counts=True)
    res = [(list(k), c / len(im)) for k, c in zip(keys, cnt) if sat(k) > .3 and max(k) > 90]
    return sorted(res, key=lambda x: -x[1])[:n]


def render_svg(ctx, svg_text, out_png, size=1024, pad=0.04):
    """SVG 在浏览器里渲染成透明底 PNG（长边 size 像素），再裁掉透明边。比正则提取稳：样式、渐变、symbol 都由浏览器处理。"""
    pg = ctx.new_page(); pg.set_viewport_size({'width': size + 80, 'height': size + 80})
    b64 = base64.b64encode(svg_text.encode('utf-8')).decode()
    pg.set_content('<html><body style="margin:20px;background:transparent"><img id=i style="display:block" src="data:image/svg+xml;base64,' + b64 + '"></body></html>')
    ok = pg.evaluate("""s => new Promise(res => { const i = document.getElementById('i'); const go = () => { let w = i.naturalWidth || 300, h = i.naturalHeight || 150; const k = s / Math.max(w, h); i.style.width = w * k + 'px'; i.style.height = h * k + 'px'; res(w > 0); }; i.complete ? go() : (i.onload = go, i.onerror = () => res(false)); })""", size)
    if not ok: pg.close(); return False
    pg.wait_for_timeout(200)
    pg.locator('#i').screenshot(path=str(out_png), omit_background=True)
    pg.close()
    im = Image.open(out_png).convert('RGBA'); bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    if bb:
        p = round(max(im.size) * pad); im = im.crop((max(0, bb[0] - p), max(0, bb[1] - p), min(im.width, bb[2] + p), min(im.height, bb[3] + p)))
    im.save(out_png, optimize=True); return True


def fetch(ctx, url, referer=None):
    r = ctx.request.get(url, headers={'Referer': referer or url}, timeout=30000)
    if not r.ok: raise RuntimeError(f'HTTP {r.status}')
    return r.body(), r.headers.get('content-type', '')


# ---------------------------------------------------------------- mark：透明底的图形标记（不含文字）
def alpha_bbox(im, thr=8):
    return im.getchannel('A').point(lambda v: 255 if v > thr else 0).getbbox()


def fit_save_mark(im, out, max_side=1024):
    """裁掉空白，长边不超过 max_side（不放大位图），存 PNG。"""
    bb = alpha_bbox(im)
    if bb: im = im.crop(bb)
    if max(im.size) > max_side:
        k = max_side / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    im.save(out, optimize=True); return im


def split_wordmark(im):
    """logo 里图形和文字连在一张 svg 里时，按空白间隔把最左（或最上）的图形分出来。
    文字的字间距远小于图形和文字之间的间隔：列（行）投影上，宽度 ≥ 整体高（宽）18% 的空白才算分隔。
    返回 (图, 说明)；说明为 None 表示整张就是图形，'joined' 表示分不出来。"""
    im = im.crop(alpha_bbox(im)); a = np.asarray(im.getchannel('A')) > 16; H, W = a.shape
    def runs(proj, min_gap):                       # 投影里 False 的连续段（长度 ≥ min_gap）把它切成若干段，返回有内容的区间
        segs, st, gap = [], None, 0
        for i, v in enumerate(list(proj) + [False] * int(min_gap + 1)):
            if v:
                if st is None: st = i
                gap = 0
            elif st is not None:
                gap += 1
                if gap >= min_gap: segs.append((st, i - gap + 1)); st = None
        return segs
    cols = runs(a.any(0), max(3, 0.18 * H))
    if len(cols) >= 2:
        x0, x1 = cols[0]; w, h = x1 - x0, H
        if 0.3 <= w / h <= 2.4: return im.crop((x0, 0, x1, H)), f'与文字相连的 svg，按间隔分出最左的图形（共 {len(cols)} 块）'
    rows = runs(a.any(1), max(3, 0.18 * W))
    if len(rows) >= 2:
        y0, y1 = rows[0]
        if 0.3 <= W / (y1 - y0) <= 2.4: return im.crop((0, y0, W, y1)), f'与文字上下排列的 svg，按间隔分出最上的图形（共 {len(rows)} 块）'
    if W / H <= 2.0: return im, None
    return im, 'joined'


def drop_plate(im, tol=40):
    """图标带纯色底板（含圆角底板）时去掉。返回 (图, 说明)；没有底板返回 (原图, None)；底板不是纯色（渐变）返回 (原图, 'gradient')。"""
    arr = np.asarray(im.convert('RGBA')).astype(float); H, W = arr.shape[:2]
    ring = np.concatenate([arr[:3].reshape(-1, 4), arr[-3:].reshape(-1, 4), arr[:, :3].reshape(-1, 4), arr[:, -3:].reshape(-1, 4)])
    mids = np.concatenate([arr[:3, W // 3:2 * W // 3].reshape(-1, 4), arr[-3:, W // 3:2 * W // 3].reshape(-1, 4), arr[H // 3:2 * H // 3, :3].reshape(-1, 4), arr[H // 3:2 * H // 3, -3:].reshape(-1, 4)])
    op = mids[mids[:, 3] > 200]
    if len(op) < len(mids) * .5: return im, None                          # 边缘中段是透明的：没有底板
    if op[:, :3].std(0).mean() > 22: return im, 'gradient'
    bgc = np.median(op[:, :3], axis=0)
    return key_out(im, bgc, tol)[0], f'去掉底板 {hexc(bgc)}'


def as_mark(ctx, kind, data, w, h, name, how):
    """把一个来源渲染成透明底的图形标记。data：svg 文本或位图字节。返回 dict(img, reliable, source, note) 或 None。"""
    tmp = RAW / f'{name}_mark_tmp.png'
    if kind == 'svg':
        size = int(min(4096, 1024 * max(1.0, (w / h) if h else 1)))           # 宽的 svg 渲染大一些，分出图形后仍有足够像素
        if not render_svg(ctx, data, tmp, size=size, pad=0.0): return None
        im = Image.open(tmp).convert('RGBA'); tmp.unlink(missing_ok=True)
        if not alpha_bbox(im): return None
        im, note = split_wordmark(im); notes = [note] if note and note != 'joined' else []
        rel_ok = note != 'joined'
        if note == 'joined': notes.append('图形和文字连在一起，分不出来，输出的是整个 logo')
        im, plate = drop_plate(im)
        if plate == 'gradient': notes.append('带渐变底板，没有去掉'); rel_ok = False
        elif plate: notes.append(plate)
        return {'img': im, 'reliable': rel_ok, 'source': how, 'note': '；'.join(notes)}
    im = Image.open(__import__('io').BytesIO(data)); im.load(); im = im.convert('RGBA')
    im, plate = drop_plate(im)
    notes = [f'位图 {im.width}×{im.height}']; rel_ok = True
    if plate == 'gradient': notes.append('带渐变底板，没有去掉'); rel_ok = False
    elif plate: notes.append(plate)
    bb = alpha_bbox(im)
    if not bb or (np.asarray(im.getchannel('A')) < 10).mean() > .97: return None
    bb2 = alpha_bbox(im); side = max(bb2[2] - bb2[0], bb2[3] - bb2[1])
    if side < 400: notes.append(f'图形只有 {side} 像素，放大到屏幕的一半以上会糊，大图镜头改用 svg 来源或自己画'); rel_ok = rel_ok and side >= 120
    return {'img': im, 'reliable': rel_ok, 'source': how, 'note': '；'.join(notes)}


def find_mark(ctx, info, url, name):
    """按优先级找图形标记：页头首页链接里的 svg → svg 图标（icon / mask-icon）→ 位图图标（去底板）。
    第一个可靠的来源直接采用；都不可靠就用第一个能出图的并在 brand.json 注明。"""
    found = []
    def take(r):
        if r: found.append(r)
        return bool(r and r['reliable'])
    phase('提取 mark：页头 logo')
    homes = sorted([h for h in info.get('homes', []) if h['w'] >= 8], key=lambda h: (h['x'], h['y']))
    pick = next((h for h in homes if h['w'] / max(h['h'], 1) <= 2.2), None) or (min(homes, key=lambda h: abs(h['w'] / max(h['h'], 1) - 1)) if homes else None)
    if pick:
        try:
            if pick['kind'] == 'svg':
                if take(as_mark(ctx, 'svg', pick['svg'], pick['w'], pick['h'], name, '页头首页链接里的内联 <svg>')): return found[-1]
            elif re.search(r'\.svg(\?|$)', pick['src']):
                data, _ = fetch(ctx, pick['src'], url)
                if take(as_mark(ctx, 'svg', data.decode('utf-8', 'ignore'), pick['w'], pick['h'], name, '页头首页链接里的 <img> svg：' + pick['src'][:80])): return found[-1]
        except Exception as e:
            print('   页头 logo 提取 mark 失败：', str(e)[:80])
    phase('提取 mark：图标')
    links = info['links']
    svgs = [l for l in links if 'svg' in l['type'] or l['href'].split('?')[0].endswith('.svg') or l['rel'] == 'mask-icon']
    bitmaps = sorted([l for l in links if l not in svgs], key=lambda l: int((re.findall(r'\d+', l['sizes']) or ['0'])[0]) + (1000 if 'apple' in l['rel'] else 0), reverse=True)
    for l in svgs[:2]:
        try:
            data, _ = fetch(ctx, l['href'], url)
            txt = data.decode('utf-8', 'ignore')
            if l['rel'] == 'mask-icon' and 'fill' not in txt[:2000]: txt = txt.replace('<svg', '<svg fill="#000"', 1)
            if take(as_mark(ctx, 'svg', txt, 1, 1, name, f'{l["rel"]} svg：{l["href"][:80]}')): return found[-1]
        except Exception as e:
            print('   svg 图标失败：', l['href'][:70], str(e)[:60])
    for l in bitmaps[:3]:
        try:
            data, _ = fetch(ctx, l['href'], url)
            if take(as_mark(ctx, 'bitmap', data, 0, 0, name, f'{l["rel"]}：{l["href"][:80]}')): return found[-1]
        except Exception as e:
            print('   位图图标失败：', l['href'][:70], str(e)[:60])
    return found[0] if found else None


def cmd_brand(a):
    url, name = a.url, a.name or default_name(a.url); mark_info = None
    RAW.mkdir(parents=True, exist_ok=True)
    with browse(a.width, a.height, 1, a.dark, a.mobile, a.timeout) as ctx:
        pg, notes, log = open_site(ctx, url, a)
        phase('分析 logo 和品牌色')
        info = pg.evaluate(JS_LOGO); col = pg.evaluate(JS_COLORS)
        top = RAW / f'{name}_brandtop.png'; pg.screenshot(path=str(top))
        font_urls = list(dict.fromkeys(pg.fonts))
        files = []; got = []
        # 1) logo：页头里的 SVG / 图片，按得分最高的来
        done = False
        for c in info['cands']:
            out = IMGDIR / f'{name}_logo.png'; IMGDIR.mkdir(parents=True, exist_ok=True)
            if c['kind'] == 'svg':
                (RAW / f'{name}_logo.svg').write_text(c['svg'], encoding='utf-8')
                if render_svg(ctx, c['svg'], out):
                    got.append(f'页头内联 SVG（{c["w"]:.0f}×{c["h"]:.0f}，得分 {c["score"]}）'); files += [RAW / f'{name}_logo.svg', out]; done = True; break
            else:
                try:
                    data, ct = fetch(ctx, c['src'], url)
                    if 'svg' in ct or c['src'].split('?')[0].endswith('.svg'):
                        (RAW / f'{name}_logo.svg').write_bytes(data)
                        if render_svg(ctx, data.decode('utf-8', 'ignore'), out): got.append(f'页头 <img> SVG：{c["src"][:90]}'); files += [RAW / f'{name}_logo.svg', out]; done = True; break
                    else:
                        raw = RAW / f'{name}_logo_raw{Path(urlparse(c["src"]).path).suffix or ".png"}'; raw.write_bytes(data)
                        im = Image.open(raw); got.append(f'页头 <img> 位图 {im.width}×{im.height}：{c["src"][:90]}（位图 logo 可能带底色，用 prep --key 去底）')
                        save_web(im, f'{name}_logo'); files += [raw, IMGDIR / f'{name}_logo.png' if (IMGDIR / f'{name}_logo.png').exists() else IMGDIR / f'{name}_logo.jpg']; done = True; break
                except Exception as e:
                    print('   候选 logo 下载失败：', str(e)[:80])
        if not done: warn('页头没找到 logo。看下面的图标候选，或用 images 下载、--hide/--wait 重试。')
        # 2) 图标：favicon / apple-touch-icon / svg icon，取最大的；og:image 当分享图
        icons = sorted(info['links'], key=lambda l: (l['href'].endswith('.svg') or 'svg' in l['type'], int((re.findall(r'\d+', l['sizes']) or ['0'])[0])), reverse=True)
        for l in icons[:3]:
            try:
                data, ct = fetch(ctx, l['href'], url); out = IMGDIR / f'{name}_icon.png'
                if 'svg' in ct or l['href'].split('?')[0].endswith('.svg'):
                    (RAW / f'{name}_icon.svg').write_bytes(data)
                    if not render_svg(ctx, data.decode('utf-8', 'ignore'), out): continue
                    files += [RAW / f'{name}_icon.svg', out]
                else:
                    raw = RAW / f'{name}_icon_raw.png'; raw.write_bytes(data); im = Image.open(raw)
                    if max(im.size) < 48: continue
                    save_web(im, f'{name}_icon'); files += [raw, out]
                got.append(f'图标：{l["rel"]} {l["href"][:90]}'); break
            except Exception as e:
                print('   图标下载失败：', l['href'][:80], str(e)[:60])
        mk = None
        try:
            mk = find_mark(ctx, info, url, name)
        except Exception as e:
            print('   mark 提取失败：', str(e)[:100])
        if mk:
            mp = IMGDIR / f'{name}_mark.png'; IMGDIR.mkdir(parents=True, exist_ok=True); im = fit_save_mark(mk['img'], mp)
            files.append(mp); mark_info = {'file': rel(mp), 'size': list(im.size), 'source': mk['source'], 'reliable': mk['reliable'], 'note': mk['note']}
            got.append(f'mark（透明底图形标记）{im.width}×{im.height}：{mk["source"]}' + ('' if mk['reliable'] else '【不可靠】') + (f'（{mk["note"]}）' if mk['note'] else ''))
            if not mk['reliable']: warn('mark 不可靠：' + mk['note'] + '。看 frames/_view/assets_sheet.jpg 里的 ' + f'{name}_mark，不对就手工用 prep 处理图标，或自己画。')
        else:
            warn('没有找到图形标记（页头首页链接里没有 svg，也没有可用的图标）。')
        phase('下载 og 图')
        if info['og']:
            try:
                data, ct = fetch(ctx, urljoin(url, info['og']), url); ext = '.png' if 'png' in ct else '.jpg'
                raw = RAW / f'{name}_og{ext}'; raw.write_bytes(data); im = Image.open(raw); save_web(im, f'{name}_og')
                got.append(f'og:image {im.width}×{im.height}'); files += [raw, IMGDIR / f'{name}_og.jpg' if (IMGDIR / f'{name}_og.jpg').exists() else IMGDIR / f'{name}_og.png']
            except Exception as e:
                print('   og:image 下载失败：', str(e)[:80])
    # 3) 品牌色
    bg = col['bodyBg']; ink = col['bodyInk'] or col['h1Ink'] or [20, 20, 20]
    votes = []                                   # (颜色, 权重, 来源)
    for k, v in col['vars'].items():
        if k.startswith('dark:') and not a.dark: continue
        if re.search(r'(^|-)(rt|success|error|warning|danger|info|tooltip|toast|alert|destructive|chart|ring|border|muted)', k, re.I): continue      # 状态色、提示框色不是品牌色
        w = 6 if re.search(r'primary|brand|accent|main|theme', k, re.I) else 0           # 只信语义名字；调色板式的变量（blue-500、brown-400）整套都在，不代表品牌用了
        if w and sat(v) > .25: votes.append((v, w, 'CSS 变量 ' + k))
    from collections import Counter
    for c, n in Counter(map(tuple, col['btn'])).items(): votes.append((list(c), min(n, 4) * 3, f'按钮背景 ×{n}'))
    for c, n in col['tx']:
        if sat(c) > .3: votes.append((c, min(n / 8, 8), f'文字色，{n} 个字'))
    for c, n in col['bgs']:
        if sat(c) > .3: votes.append((c, min(n * 60, 10), f'背景色，面积 {n:.0%}'))
    for c, n in Counter(map(tuple, col['link'])).items():
        if sat(c) > .3: votes.append((list(c), min(n, 6), f'链接色 ×{n}'))
    if col.get('themeColor'):
        try:
            tc = [int(col['themeColor'].lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]; votes.append((tc, 4, 'meta theme-color'))
        except Exception: pass
    logo_png = IMGDIR / f'{name}_logo.png'
    if logo_png.exists():
        arr = np.asarray(Image.open(logo_png).convert('RGBA').resize((64, 64))).reshape(-1, 4); m = arr[arr[:, 3] > 200][:, :3]
        if len(m):
            q = (m // 24 * 24 + 12).astype(int); ks, cn = np.unique(q, axis=0, return_counts=True); k = ks[cn.argmax()]
            votes.append((list(k), 5 if sat(k) > .25 else 2, 'logo 主色'))
    for c, share in screenshot_colors(top): votes.append((c, round(share * 40, 1), f'首屏面积 {share:.0%}'))
    clusters = []                                 # 相近的色合并，权重相加
    for c, w, why in votes:
        if dist(c, bg) < 40 or w <= 0: continue
        for cl in clusters:
            if dist(cl['c'], c) < 36 or (sat(c) > .3 and sat(cl['c']) > .3 and hue_gap(cl['c'], c) < .05):     # 同色相的深浅变体算同一个色
                cl['w'] += w; cl['why'].append(why)
                if 'CSS 变量' in why or '按钮' in why: cl['c'] = c            # 以页面里真实写的色值为准，不用截图量化值
                break
        else: clusters.append({'c': c, 'w': w, 'why': [why]})
    sa = sorted([c for c in clusters if sat(c['c']) > .22], key=lambda c: -c['w'])[:3]
    neutral_acc = False
    if not sa:                                    # 黑白灰品牌（Notion、Vercel 之类）
        neutral_acc = True; sa = [{'c': ink, 'w': 1, 'why': ['页面无饱和强调色，用正文色']}]
    colors = {'bg': bg, 'ink': ink, 'ink2': mix(ink, bg, .45), 'dim': mix(bg, ink, .12), 'acc': sa[0]['c']}
    if len(sa) > 1: colors['acc2'] = sa[1]['c']
    if len(sa) > 2: colors['acc3'] = sa[2]['c']
    use = {'bg': '页面背景', 'ink': '正文色', 'acc': '主强调色（按钮、链接、logo 常用）', 'acc2': '次强调色', 'acc3': '第三强调色'}
    loaded = []
    for f in col['loaded']:
        f = pick_font(f)
        if f and f not in loaded: loaded.append(f)
    fonts = {k: pick_font(v) for k, v in col['fonts'].items()}
    for k in ('h1', 'body'):                      # 样式表里写的是系统字体栈、实际加载的是网络字体（Tailwind + next/font 常见）：用加载的那个
        if loaded and (not fonts[k] or fonts[k] not in loaded) and not re.search(r'mono|code', loaded[0], re.I): fonts[k] = loaded[0]
    # 输出
    print(f'\n== {name} 品牌信息 ==')
    for g in got: print('  ✓', g)
    if font_urls: print(f'  页面加载了 {len(font_urls)} 个字体文件，例：{font_urls[0][:100]}（字体文件需要时下载放进 web/fonts/，在 theme.font_files 里声明；没有就退回系统字体）')
    print('\n品牌色（以页面真实色值为准，来源在括号里）：')
    for k in ('bg', 'ink', 'acc', 'acc2', 'acc3'):
        if k in colors:
            ev = next((c for c in sa if c['c'] == colors[k]), None)
            print(f'  {k:4s} {hexc(colors[k])}  {use[k]}' + (f'  ← {"、".join(ev["why"][:3])}' if ev else ''))
    if neutral_acc: print('  这是黑白灰品牌：强调色用 logo 或产品里的小面积彩色点缀，别用大面积色块')
    print('\n字体：' + '  '.join(f'{k}={v or "（无）"}{"" if not v or v in loaded else "（页面没加载这个字体，可能是系统字体）"}' for k, v in fonts.items()))
    snip = {'colors': {k: hexc(v) for k, v in colors.items()}, 'fonts': {'display': fonts['h1'] or fonts['body'] or 'Helvetica Neue', 'body': fonts['body'] or fonts['h1'] or 'Helvetica Neue', 'mono': fonts['code'] or 'JetBrains Mono'}}
    print('\n可粘进 project.json 的 theme（模板自带字体只有 Instrument Serif 和 JetBrains Mono；其他字体要给文件，否则渲染时退回系统字体）：')
    print(json.dumps(snip, ensure_ascii=False, indent=2))
    bj = {'url': url, 'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dark': a.dark, 'theme': snip, 'evidence': [{'color': hexc(c['c']), 'weight': round(c['w'], 1), 'why': c['why']} for c in sa],
          'mark': mark_info, 'files': [rel(f) for f in files], 'font_files': font_urls[:20], 'site': info['site'], 'title': info['title']}
    json.dump(bj, open(ROOT / 'assets' / 'brand.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    manifest('brand', url, [f for f in files if Path(f).exists()], notes=notes)
    print('\n已写入 assets/brand.json')


# ---------------------------------------------------------------- images
JS_IMAGES = r"""
() => {
  const abs = u => { try { return new URL(u, location.href).href; } catch (_) { return null; } };
  const best = ss => { if (!ss) return null; let b = null, bw = -1; for (const p of ss.split(',')) { const [u, d] = p.trim().split(/\s+/); const w = d ? parseFloat(d) * (d.endsWith('x') ? 1000 : 1) : 0; if (w > bw) { bw = w; b = u; } } return b; };
  const found = new Map(); const add = (u, how, w, h) => { u = u && abs(u); if (!u || u.startsWith('data:')) return; if (!found.has(u)) found.set(u, { url: u, how, shown: [w || 0, h || 0] }); else { const f = found.get(u); f.shown = [Math.max(f.shown[0], w || 0), Math.max(f.shown[1], h || 0)]; } };
  document.querySelectorAll('img').forEach(i => { const r = i.getBoundingClientRect(); for (const u of [best(i.srcset), i.currentSrc, i.src, i.dataset.src, i.dataset.lazySrc, best(i.dataset.srcset)]) add(u, 'img', r.width, r.height); });
  document.querySelectorAll('picture source').forEach(s => add(best(s.srcset), 'source', 0, 0));
  document.querySelectorAll('video[poster]').forEach(v => add(v.poster, 'poster', v.clientWidth, v.clientHeight));
  document.querySelectorAll('*').forEach(e => { const b = getComputedStyle(e).backgroundImage; if (b && b.includes('url(')) for (const m of b.matchAll(/url\(["']?([^"')]+)["']?\)/g)) { const r = e.getBoundingClientRect(); add(m[1], 'bg', r.width, r.height); } });
  document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"]').forEach(m => add(m.content, 'og', 0, 0));
  return [...found.values()];
}
"""


def unwrap(u):
    """Next.js 等图片优化地址 /_next/image?url=原图&w=640：取出原图地址，原图比优化版大。"""
    q = parse_qs(urlparse(u).query)
    if ('/_next/image' in u or '/_vercel/image' in u) and 'url' in q: return urljoin(u, q['url'][0])
    return u


def cmd_images(a):
    url, name = a.url, a.name or default_name(a.url)
    RAW.mkdir(parents=True, exist_ok=True)
    with browse(a.width, a.height, 1, a.dark, a.mobile, a.timeout) as ctx:
        pg, notes, log = open_site(ctx, url, a)
        cand = pg.imgs                                   # open_site 滚到底（含内部滚动容器和浮层）之后、关弹窗之前收集的
        seen, rows, svgs = set(), [], []
        for c in cand:
            u = unwrap(c['url'])
            if u in seen: continue
            seen.add(u)
            if re.search(r'\.svg(\?|$)', u): svgs.append(u); continue
            if re.search(r'(pixel|beacon|track|analytics|1x1|spacer|\.gif\?)|/collect\?|doubleclick|facebook\.com/tr', u, re.I): continue
            try:
                data, ct = fetch(ctx, u, url)
                im = Image.open(__import__('io').BytesIO(data)); im.load()
            except Exception:
                continue
            w, h = im.size
            if max(w, h) < a.min_size or min(w, h) < 120 or max(w, h) / max(1, min(w, h)) > 8: continue
            rows.append({'u': u, 'how': c['how'], 'w': w, 'h': h, 'shown': c['shown'], 'data': data, 'im': im, 'hash': hashlib.md5(data).hexdigest()})
    uniq = {}
    for r in rows: uniq.setdefault(r['hash'], r)
    ICONISH = re.compile(r'logo|badge|avatar|icon|favicon|brand|partner|trusted|sprite|flag|plugin|testimonial|portrait', re.I)
    for r in uniq.values():                          # 排序分：原图面积；小图标、徽章、客户 logo、页面上显示很小的图降权，让产品界面图排在前面
        r['score'] = min(r['w'] * r['h'], 4e6) * (.25 if ICONISH.search(r['u']) else 1) * (.15 if 0 < max(r['shown']) < 100 else 1)
    rows = sorted(uniq.values(), key=lambda r: -r['score'])
    if not rows:
        warn(f'没拿到 ≥{a.min_size}px 的图片。页面可能用 canvas/视频渲染，或被拦截。' + (f'另有 {len(svgs)} 个 SVG（插图可用 brand 的渲染方式）。' if svgs else '') + '\n   ' + ALT); return
    pick = re.compile(a.match, re.I) if a.match else None
    files = []; used = set(); n_in = 0
    print(f'\n共 {len(rows)} 张（≥{a.min_size}px），产品图、大图排在前面；' + (f'地址匹配 {a.match!r} 的放进 web/img/' if pick else f'前 {a.max} 张放进 web/img/（--match 正则 可按地址挑，--max 调数量）') + '，全部原图在 assets/raw/：')
    for i, r in enumerate(rows, 1):
        base = f'{name}_img_{slug(Path(urlparse(r["u"]).path).stem, 22)}'
        if base in used: base += f'_{i}'
        used.add(base)
        ext = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp', 'GIF': '.gif'}.get(r['im'].format, '.jpg')
        raw = RAW / f'{base}{ext}'; raw.write_bytes(r['data']); files.append(raw)
        tag = ''
        if (pick.search(r['u']) if pick else i <= a.max) and n_in < 60:
            im = r['im']; im = im.convert('RGBA') if im.mode in ('P', 'LA', 'RGBA') else im.convert('RGB')
            p = save_web(im, base); files.append(p); tag = f'→ web/img/{p.name}'; n_in += 1
        if i <= 40 or tag: print(f'  {i:2d}. {r["w"]}×{r["h"]}  {r["how"]:6s} 页面显示 {r["shown"][0]:.0f}×{r["shown"][1]:.0f}  {base}{ext} {tag}\n      {r["u"][:110]}')
    if svgs: print(f'另有 {len(svgs)} 个 SVG 未下载（多是图标和插图）。')
    manifest('images', url, files, notes=notes)


# ---------------------------------------------------------------- frames / prep / sheet
def cmd_frames(a):
    src = Path(a.video)
    if not src.exists(): sys.exit(f'找不到视频：{src}')
    name = a.name or slug(src.stem, 24)
    out = IMGDIR / name
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    vf = f'fps={a.fps}' + (f',scale={a.width}:-2' if a.width else '')
    cmd = [ffmpeg(), '-y', '-v', 'error']
    if a.start: cmd += ['-ss', str(a.start)]
    if a.end: cmd += ['-to', str(a.end)]
    cmd += ['-i', str(src), '-vf', vf, '-q:v', '3', str(out / '%04d.jpg')]
    r = subprocess.run(cmd, capture_output=True, text=True)
    fr = sorted(out.glob('*.jpg'))
    if r.returncode or not fr: sys.exit('ffmpeg 失败：' + r.stderr[-300:])
    im = Image.open(fr[0]); mb = len(fr) * im.width * im.height * 4 / 1e6
    print(f'✓ web/img/{name}/  {len(fr)} 帧  {im.width}×{im.height}  {a.fps} fps  时长 {len(fr) / a.fps:.2f}s')
    print(f'用法：const f = seqFrame(\'{name}\', lt, {a.fps}); if (f) img(ctx, f, x, y, w, h, {{fit:\'cover\', r:24}});   // lt = 镜头内本地时间；第三个参数用 true 循环')
    print(f'      SEQ.{name} 也可以自己按下标取；project.json 的 assets.sequences 写 "auto" 即可自动扫描')
    if mb > 1500: warn(f'全部解码约占内存 {mb / 1000:.1f} GB，可能让渲染变慢或崩溃。用 --width 960、--fps 15 或缩短 --start/--end。')
    elif len(fr) > 400: warn(f'{len(fr)} 帧偏多，加载变慢。需要时降 --fps 或截短。')
    manifest('frames', str(src), [fr[0], fr[-1]], sequence=f'web/img/{name}/', frames=len(fr), fps=a.fps)


def key_out(im, bgc, tol=40):
    """去掉和图片边缘相连的底色（也包括已经透明的像素，圆角底板的四角就是透明的）。返回 (RGBA 图, 透明占比)。
    底色和图形之间留 tol 到 2×tol 的过渡带，做半透明边并反算前景色，避免白边。"""
    from scipy import ndimage
    arr = np.asarray(im.convert('RGBA')).astype(float); rgb = arr[..., :3]
    d = np.sqrt(((rgb - bgc) ** 2).sum(-1))
    near = (d < tol) | (arr[..., 3] < 10)
    lab, n = ndimage.label(near)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgmask = np.isin(lab, list(edge))
    soft = ndimage.binary_dilation(bgmask, iterations=2) & ~bgmask
    al = np.where(bgmask, 0.0, 1.0)
    t = np.clip((d - tol) / max(1, tol), 0, 1)
    al = np.where(soft, np.minimum(1, t), al)
    fg = rgb.copy(); m = soft & (al > 0.02)
    fg[m] = np.clip((rgb[m] - (1 - al[m, None]) * bgc) / al[m, None], 0, 255)
    arr[..., :3] = fg; arr[..., 3] = arr[..., 3] * al
    return Image.fromarray(arr.astype(np.uint8)), float((arr[..., 3] < 10).mean())


def cmd_prep(a):
    src = Path(a.image)
    if not src.exists(): sys.exit(f'找不到图片：{src}')
    name = a.name or slug(src.stem, 28)
    RAW.mkdir(parents=True, exist_ok=True); shutil.copy2(src, RAW / src.name) if src.resolve().parent != RAW.resolve() else None
    if src.suffix.lower() == '.svg':
        with browse(900, 900, 1, timeout=a.timeout) as ctx:
            tmp = RAW / f'{name}_svg.png'
            if not render_svg(ctx, src.read_text(encoding='utf-8', errors='ignore'), tmp, size=a.max): sys.exit('SVG 渲染失败：缺少宽高或 viewBox，或引用了外部资源。')
        im = Image.open(tmp).convert('RGBA')
    else:
        im = Image.open(src); im = im.convert('RGBA')
    if a.key and np.asarray(im)[..., 3].min() < 250:
        print('这张图本来就有透明通道，跳过去底。'); a.key = None
    if a.key:                                                     # 去底：只去掉和边缘相连的底色，图形内部的同色不动
        if a.key == 'auto':
            rgb = np.asarray(im).astype(float)[..., :3]
            ed = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]); bgc = np.median(ed, axis=0)
            if ed.std(0).mean() > 25: sys.exit('四边颜色不一致，不是纯色底，自动去底会误伤。换 --key "#rrggbb" 指定底色，或换一张本身透明的图（SVG、PNG）。')
        else:
            bgc = np.array([int(a.key.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)], float)
        im, tr = key_out(im, bgc, a.tol)
        print(f'去底：底色 {hexc(bgc)}，容差 {a.tol}；透明占比 {tr:.0%}' + ('。占比超过 35%，图形很可能被吃掉：这多半是满版的方形图标，不需要去底，用 --round 0.225 做圆角即可' if tr > .35 else '。太低说明底色不纯，调 --tol 或用 --key "#rrggbb"' if tr < .02 else ''))
    if a.round:                                                   # 方形 App 图标做圆角透明（iOS 风格约 0.225）
        m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=a.round * min(im.size), fill=255)
        im.putalpha(Image.fromarray(np.minimum(np.asarray(im.getchannel('A')), np.asarray(m))))
    if a.exposure != 1 or a.contrast != 1:                        # 调亮度和对比度：只动颜色，保留透明度。对比围绕中灰 128
        arr = np.asarray(im.convert('RGBA')).astype(float); c = arr[..., :3] * a.exposure
        arr[..., :3] = np.clip((c - 128) * a.contrast + 128, 0, 255)
        im = Image.fromarray(arr.astype(np.uint8))
        print(f'调色：亮度 ×{a.exposure:g}，对比 ×{a.contrast:g}')
    if a.trim:
        bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
        if bb: im = im.crop(bb)
    if max(im.size) > a.max:
        s = a.max / max(im.size); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    p = save_web(im, name, long_max=a.max)
    print(f'✓ {rel(p)}  {im.width}×{im.height}')
    manifest('prep', str(src), [p])


def cmd_sheet(a):
    VIEW.mkdir(parents=True, exist_ok=True)
    items = []
    if IMGDIR.exists():
        for f in sorted(IMGDIR.iterdir()):
            if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif'): items.append((f.stem, f, None))
            elif f.is_dir():
                fr = sorted(x for x in f.iterdir() if x.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'))
                if fr: items.append((f.name, fr[len(fr) // 2], len(fr)))
    if not items: print('web/img/ 里还没有素材。'); return
    COLS, CW, TH, LH = 4, 390, 230, 38
    from PIL import ImageFont
    font = None
    for fp in ('/System/Library/Fonts/STHeiti Light.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc', '/System/Library/Fonts/PingFang.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'):
        try: font = ImageFont.truetype(fp, 13); break
        except Exception: pass
    bj = ROOT / 'assets' / 'brand.json'; swatches = []
    if bj.exists():
        try: swatches = list(json.load(open(bj, encoding='utf-8'))['theme']['colors'].items())
        except Exception: pass
    per = COLS * 5; pages = [items[i:i + per] for i in range(0, len(items), per)]
    paths = []
    for pi, pg in enumerate(pages):
        rows = (len(pg) + COLS - 1) // COLS; top = 44 if swatches and pi == 0 else 0
        sh = Image.new('RGB', (COLS * CW, top + rows * (TH + LH)), (28, 28, 30)); d = ImageDraw.Draw(sh)
        for k, (nm, c) in enumerate(swatches if pi == 0 else []):
            d.rectangle([8 + k * 150, 8, 36 + k * 150, 36], fill=c); d.text((42 + k * 150, 16), f'{nm} {c}', fill=(220, 220, 220), font=font)
        for j, (nm, f, nfr) in enumerate(pg):
            x, y = (j % COLS) * CW, top + (j // COLS) * (TH + LH)
            im = Image.open(f); im.load(); W0, H0 = im.size; alpha = im.mode in ('RGBA', 'LA', 'P') and im.convert('RGBA').getchannel('A').getextrema()[0] < 250
            s = min((CW - 12) / W0, TH / H0); tw, thh = max(1, int(W0 * s)), max(1, int(H0 * s))
            t = im.convert('RGBA').resize((tw, thh), Image.LANCZOS); cell = Image.new('RGB', (tw, thh), (40, 40, 42))
            if alpha:                                                  # 透明图画棋盘格，白 logo 和黑 logo 都看得见
                ck = np.indices((thh, tw)).sum(0) // 12 % 2; cell = Image.fromarray(np.where(ck[..., None] == 0, 96, 140).astype(np.uint8).repeat(3, -1))
            cell.paste(t, (0, 0), t); sh.paste(cell, (x + 6 + (CW - 12 - tw) // 2, y + 4 + (TH - thh) // 2))
            lab = f'{nm}  {W0}x{H0}' + (f'  序列 {nfr} 帧' if nfr else '') + ('  透明' if alpha else '')
            d.text((x + 8, y + TH + 6), lab[:60], fill=(255, 220, 0), font=font); d.text((x + 8, y + TH + 22), (f'SEQ.{nm}' if nfr else f'IMG.{nm}'), fill=(150, 150, 150), font=font)
        p = VIEW / ('assets_sheet.jpg' if pi == 0 else f'assets_sheet_{pi + 1}.jpg'); sh.save(p, quality=85); paths.append(p)
    for p in paths: print(f'✓ {rel(p)}')
    print(f'共 {len(items)} 项素材。只读这张缩小的总览，不要直接读原图。')


# ---------------------------------------------------------------- 命令行
def _main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)

    def web(p):
        p.add_argument('--width', type=int, default=1440); p.add_argument('--height', type=int, default=900); p.add_argument('--dpr', type=float, default=2)
        p.add_argument('--mobile', action='store_true'); p.add_argument('--dark', action='store_true'); p.add_argument('--wait', type=float, default=2)
        p.add_argument('--hide', action='append', default=[]); p.add_argument('--click', action='append', default=[])
        p.add_argument('--full-max', type=int, default=6000, help='整页长图最大 CSS 高度')
        p.add_argument('--timeout', type=float, default=120, help='浏览器阶段的总时限（秒），超时杀掉 Chrome 并退出')
    p = sp.add_parser('shot'); p.add_argument('url'); p.add_argument('name', nargs='?'); web(p)
    p = sp.add_parser('zoom'); p.add_argument('url'); p.add_argument('name'); p.add_argument('targets', nargs='+'); web(p)
    p.add_argument('--zdpr', type=float, default=3, help='高清局部的像素比'); p.add_argument('--pad', type=float, default=0, help='目标四周多留的 CSS 像素'); p.add_argument('--tag', help='输出名后缀，逗号分隔，对应各目标')
    p = sp.add_parser('brand'); p.add_argument('url'); p.add_argument('name', nargs='?'); web(p)
    p = sp.add_parser('images'); p.add_argument('url'); p.add_argument('name', nargs='?'); web(p)
    p.add_argument('--min-size', type=int, default=400, help='长边小于它的图丢弃'); p.add_argument('--max', type=int, default=12, help='放进 web/img/ 的张数'); p.add_argument('--match', help='只把地址匹配这个正则的图放进 web/img/（如 "landing-page/(use|using|chat)"）')
    p = sp.add_parser('frames'); p.add_argument('video'); p.add_argument('name', nargs='?'); p.add_argument('--fps', type=float, default=30)
    p.add_argument('--start', type=float); p.add_argument('--end', type=float); p.add_argument('--width', type=int, default=1280)
    p = sp.add_parser('prep'); p.add_argument('image'); p.add_argument('name', nargs='?'); p.add_argument('--max', type=int, default=2400, help='长边上限')
    p.add_argument('--key', nargs='?', const='auto', help='去掉和边缘相连的纯色底：auto 或 "#ffffff"'); p.add_argument('--tol', type=float, default=40); p.add_argument('--timeout', type=float, default=120); p.add_argument('--trim', action='store_true', help='裁掉透明边'); p.add_argument('--round', type=float, help='圆角比例（占短边），方形 App 图标用 0.225')
    p.add_argument('--exposure', type=float, default=1, help='亮度倍数（深色产品截图放在深色舞台上看不见时用 1.4）'); p.add_argument('--contrast', type=float, default=1, help='对比倍数，围绕中灰；大于 1 暗部更暗，只用于发灰的图')
    sp.add_parser('sheet')
    a = ap.parse_args()
    if getattr(a, 'mobile', False) and a.width == 1440: a.width, a.height = 390, 844
    if a.cmd in ('shot', 'zoom'):
        a.tag = getattr(a, 'tag', None); a.zdpr = getattr(a, 'zdpr', 2); a.pad = getattr(a, 'pad', 0)
        name = a.name or default_name(a.url)
        a.cdpr = max(a.dpr, a.zdpr) if a.cmd == 'zoom' else a.dpr
        with browse(a.width, a.height, a.cdpr, a.dark, a.mobile, a.timeout) as ctx:
            ok = do_shot(ctx, a.url, name, a, a.targets if a.cmd == 'zoom' else ())
        if not ok: sys.exit(2)
    else:
        globals()['cmd_' + a.cmd](a)


def main():
    """用过浏览器的命令，结束时直接退出进程：Playwright 的驱动进程收尾可能卡住，产物都已写盘，不必等它。"""
    code = 0
    try: _main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
        if isinstance(e.code, str): print(e.code, file=sys.stderr)
    except BaseException:
        import traceback; traceback.print_exc(); code = 1
    sys.stdout.flush(); sys.stderr.flush()
    if _PW: os._exit(code)
    sys.exit(code)


if __name__ == '__main__':
    main()
