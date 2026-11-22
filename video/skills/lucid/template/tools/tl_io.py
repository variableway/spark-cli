"""时间轴的公共输出：timeline.json、web/timeline.js、web/project.js，并同步 index.html 里的字体、模块、镜头脚本列表。
tools/timeline.py（节拍 / 手写）和 tools/build_timeline.py（配音）都调用 write_all。"""
import json, glob, os, re
from common import ROOT

IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')


def scan_assets(cfg):
    """assets.images 没写或写 "auto" 时，自动收集 web/img/ 顶层的图片；子目录里的编号帧当作序列（SEQ.名字）。"""
    A = dict(cfg.get('assets') or {})
    base = ROOT / 'web' / 'img'
    if A.get('images') in (None, 'auto'):
        A['images'] = sorted(f for f in os.listdir(base) if f.lower().endswith(IMG_EXT)) if base.exists() else []
    if A.get('sequences') in (None, 'auto'):
        seq = {}
        if base.exists():
            for d in sorted(os.listdir(base)):
                p = base / d
                if p.is_dir():
                    fr = sorted(f for f in os.listdir(p) if f.lower().endswith(IMG_EXT))
                    if fr: seq[d] = fr
        A['sequences'] = seq
    missing = [f for f in A['images'] if not (base / f).exists()]
    if missing:
        raise SystemExit(f'project.json 的 assets.images 里这些文件不存在：{missing}')
    return A


def sync_index(cfg):
    idx = ROOT / 'web' / 'index.html'; h = idx.read_text(encoding='utf-8')
    shots = sorted(os.path.basename(f) for f in glob.glob(str(ROOT / 'web' / 'shots_*.js')))
    mods = cfg.get('modules', [])
    for m in mods:
        if not (ROOT / 'web' / 'modules' / f'{m}.js').exists():
            raise SystemExit(f'modules 里的 {m} 不存在：web/modules/{m}.js')
    faces = ''
    for f in (cfg.get('theme') or {}).get('font_files', []):
        # 格式：{"family": "Geist", "src": "fonts/Geist-600.woff2", "weight": "600", "style": "normal"}，src 相对 web/
        if not isinstance(f, dict) or not f.get('family') or not f.get('src'):
            raise SystemExit(f'theme.font_files 每一项要写成 {{"family": "字体名", "src": "fonts/文件.woff2", "weight": "400"}}，现在是：{f!r}')
        src = re.sub(r'^url\((.*)\)$', r'\1', f['src'].strip()).strip('\'"')
        if not src.startswith(('http:', 'https:', 'data:')) and not (ROOT / 'web' / src).exists():
            raise SystemExit(f'字体文件不存在：web/{src}（theme.font_files 的 src 相对 web/ 目录）')
        faces += '@font-face{font-family:"%s";src:url("%s");font-weight:%s;font-style:%s}\n' % (f['family'], src, f.get('weight', '400'), f.get('style', 'normal'))
    h = re.sub(r'/\* fonts:start \*/.*?/\* fonts:end \*/', '/* fonts:start */\n' + faces + '/* fonts:end */', h, flags=re.S)
    h = re.sub(r'<!-- modules:start -->.*?<!-- modules:end -->', '<!-- modules:start -->\n' + ''.join(f'<script src="modules/{m}.js"></script>\n' for m in mods) + '<!-- modules:end -->', h, flags=re.S)
    h = re.sub(r'<!-- shots:start -->.*?<!-- shots:end -->', '<!-- shots:start -->\n' + ''.join(f'<script src="{f}"></script>\n' for f in shots) + '<!-- shots:end -->', h, flags=re.S)
    idx.write_text(h, encoding='utf-8')
    return shots, mods


def write_all(tl, cfg):
    json.dump(tl, open(ROOT / 'timeline.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    (ROOT / 'web' / 'timeline.js').write_text('window.TL = ' + json.dumps(tl, ensure_ascii=False) + ';\n', encoding='utf-8')
    pj = dict(cfg); pj['assets'] = scan_assets(cfg)
    (ROOT / 'web' / 'project.js').write_text('window.PROJECT = ' + json.dumps(pj, ensure_ascii=False) + ';\n', encoding='utf-8')
    shots, mods = sync_index(cfg)
    ids = set(tl['scenes'])
    defined = set()
    for f in shots:
        defined |= set(re.findall(r'SHOT\.(\w+)\s*=', (ROOT / 'web' / f).read_text(encoding='utf-8')))
    lost = sorted(defined - ids); todo = sorted(ids - defined, key=lambda s: tl['scenes'][s]['t0'])
    msg = f"镜头文件 {shots or '（还没有）'}；模块 {mods or '无'}；图片 {len(pj['assets']['images'])} 张"
    if lost: msg += f'\n  注意：这些镜头写了代码但不在时间轴里，不会被画出来：{lost}'
    if todo: msg += f'\n  还没写的镜头（渲染时显示占位）：{todo}'
    ENGINE = {'core.js', 'main.js', 'bg.js', 'gl3d.js', 'timeline.js', 'project.js'}
    stray = sorted(f.name for f in (ROOT / 'web').glob('*.js') if not f.name.startswith('shots_') and f.name not in ENGINE)
    if stray: msg += f'\n  ⚠️ web/ 下的 {stray} 不会被加载（只加载引擎文件和 shots_*.js）。共用代码请命名为 shots_*.js，例如 shots_00_common.js（按文件名排序加载）'
    return msg
