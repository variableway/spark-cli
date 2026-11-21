"""合同预检：python3 tools/lint.py
扫描 web/shots_*.js，找出违反合同（SKILL.md「合同：画面只由时间算出」）的写法。render.py 每次渲染前都会先跑它，有命中就不渲。
  未保护的衰减      Math.exp(-(t - t0) / tau) 这类写法。t 早于 t0 时（pre 重叠段、提前起手）结果是几十上百倍，元素被放大成怪形或整块画面变暗。
                    → decay(t, t0, tau)
  丢掉全局矩阵      setTransform(1, 0, 0, 1, 0, 0)。转场位移、震动、底鼓缩放都在全局矩阵里，重置后就失效了。
                    → screen(ctx) 或 cam(ctx, …)。离屏画布（同一文件里由 getContext() 得到的变量）不算。
  不由 t 决定的值    Math.random()、Date.now()、performance.now()。逐帧渲染和分段并行时，每一帧、每个进程的结果都不同。
                    → 随机数用 rng(种子)，时间只用 t
  绘制函数里登记音效  EV(…) 写在 SHOT 的绘制函数（或参数是 ctx 的函数）里。导出音效时不调用绘制函数，这些音效会全部丢失。
                    → 把 EV(…) 移到镜头文件顶层，时刻用和画面相同的表达式算
豁免：确实需要的行（例如离屏画布上的 setTransform），在行尾写注释 `// lint-ok: 原因`，原因不能空着。
"""
import re, sys
from common import ROOT

RULES = [
    (re.compile(r'Math\.exp\(\s*-\s*\(+\s*t\s*-'), '未保护的衰减 Math.exp(-(t - …))', '改成 decay(t, t0, tau)：t 早于 t0 时它返回 0，不会变成几十上百倍'),
    (re.compile(r'setTransform\(\s*1\s*,\s*0\s*,\s*0\s*,\s*1\s*,\s*0\s*,\s*0\s*\)'), 'setTransform(1, 0, 0, 1, 0, 0) 丢掉全局矩阵', '改成 screen(ctx) 或 cam(ctx, …)；如果这是离屏画布，行尾加 // lint-ok: 离屏画布'),
    (re.compile(r'\bMath\.random\s*\('), 'Math.random()', '改成 rng(种子)，同一个种子每帧结果相同'),
    (re.compile(r'\bDate\.now\s*\('), 'Date.now()', '画面只能由 t 算出，用 t'),
    (re.compile(r'\bperformance\.now\s*\('), 'performance.now()', '画面只能由 t 算出，用 t'),
]
SET_RE = re.compile(r'([\w$]+)\s*\.\s*setTransform\(\s*1\s*,\s*0\s*,\s*0\s*,\s*1\s*,\s*0\s*,\s*0\s*\)')
OFF_RE = re.compile(r'([\w$]+)\s*=\s*[^;,=]*?\.getContext\s*\(')   # 离屏画布的 2D 上下文
EV_RE = re.compile(r'(?<![\w$.])EV\s*\(')
OK_RE = re.compile(r'//\s*lint-ok:\s*\S')
KEYWORDS = {'if', 'for', 'while', 'switch', 'catch', 'with', 'return', 'function'}
# 绘制函数的开头：SHOT.X = function (…) / SHOT.X = (…) =>、draw(…) { 方法、以及第一个参数叫 ctx 的函数
DRAW_HEAD = [re.compile(r'SHOT\s*(?:\.\s*\w+|\[[^\]]+\])\s*=\s*(?:function\s*[\w$]*\s*\([^)]*\)|\([^)]*\)\s*=>|[\w$]+\s*=>)\s*$'),
             re.compile(r'(?:^|[^\w$.])draw\s*\([^)]*\)\s*$'),
             re.compile(r'(?:^|[^\w$.])draw\s*:\s*(?:function\s*[\w$]*\s*\([^)]*\)|\([^)]*\)\s*=>)\s*$'),
             re.compile(r'function\s*[\w$]*\s*\(\s*ctx\b[^)]*\)\s*$'),
             re.compile(r'\(\s*ctx\b[^)]*\)\s*=>\s*$')]


def strip_code(src):
    """去掉注释和字符串内容（换成空格，保留换行），行号不变。模板字符串里的 ${…} 当普通代码处理不了，整段当字符串。"""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]; nx = src[i + 1] if i + 1 < n else ''
        if c == '/' and nx == '/':
            j = src.find('\n', i); j = n if j < 0 else j; out.append(' ' * (j - i)); i = j
        elif c == '/' and nx == '*':
            j = src.find('*/', i + 2); j = n if j < 0 else j + 2; out.append(re.sub(r'[^\n]', ' ', src[i:j])); i = j
        elif c in '\'"`':
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == '\\': j += 1
                elif src[j] == '\n' and c != '`': break
                j += 1
            j = min(n, j + 1); out.append(c + re.sub(r'[^\n]', ' ', src[i + 1:j - 1]) + (c if j - 1 > i else '')); i = j
        else:
            out.append(c); i += 1
    return ''.join(out)


def ev_in_draw(code):
    """返回写在绘制函数里的 EV( 所在行号。按花括号层级跟踪：进入绘制函数体后，里面（含嵌套）的 EV 都算。"""
    hits, stack, head_start, line = [], [], 0, 1
    i = 0
    while i < len(code):
        c = code[i]
        if c == '\n': line += 1
        if c == '{':
            head = code[head_start:i].replace('\n', ' ')
            draw = any(p.search(head) for p in DRAW_HEAD)
            stack.append(draw or (bool(stack) and stack[-1])); head_start = i + 1
        elif c == '}':
            if stack: stack.pop()
            head_start = i + 1
        elif c == ';':
            head_start = i + 1
        elif c == 'E' and stack and stack[-1]:
            m = EV_RE.match(code, i)
            if m and (i == 0 or not re.match(r'[\w$.]', code[i - 1])): hits.append(line)
        i += 1
    return hits


def lint():
    """[(文件名, 行号, 问题, 改法, 原行)]"""
    found = []
    for f in sorted((ROOT / 'web').glob('shots_*.js')):
        src = f.read_text(encoding='utf-8'); lines = src.split('\n'); code = strip_code(src); clines = code.split('\n')
        ok = {k + 1 for k, s in enumerate(lines) if OK_RE.search(s)}
        off = set(OFF_RE.findall(code))
        for k, s in enumerate(clines):
            if k + 1 in ok: continue
            for rx, what, fix in RULES:
                if rx is RULES[1][0]:
                    if any(m.group(1) not in off for m in SET_RE.finditer(s)): found.append((f.name, k + 1, what, fix, lines[k].strip()))
                elif rx.search(s): found.append((f.name, k + 1, what, fix, lines[k].strip()))
        for ln in sorted(set(ev_in_draw(code))):
            if ln not in ok:
                found.append((f.name, ln, '绘制函数里调用 EV()', '移到镜头文件顶层（只执行一次），时刻用和画面相同的表达式（b(8)、S.t0 + 0.4、ph(…)）', lines[ln - 1].strip()))
    return sorted(found)


def report(found):
    print(f'[合同预检] {len(found)} 处违反合同的写法，没有开始渲染：')
    for fn, ln, what, fix, src in found[:30]:
        print(f'  web/{fn}:{ln}  {what}\n      {src[:120]}\n      → {fix}')
    if len(found) > 30: print(f'  … 还有 {len(found) - 30} 处')
    print('确实需要的行在行尾写 // lint-ok: 原因')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'): print(__doc__); sys.exit(0)
    r = lint()
    if r: report(r); sys.exit(1)
    print('[合同预检] 通过')
