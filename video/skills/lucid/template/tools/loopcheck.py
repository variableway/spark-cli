"""循环接缝检查：python3 tools/loopcheck.py [--format 名字]
project.json 要有 "loop": true（运动模糊的子帧才会越过首尾，render(t) 才按 total 取模）。
接缝是「最后一帧 → 第 0 帧」这一步，它应当和片内任何地方一样平滑：位置不跳，速度不突变。检查：
  1. render(total) 与 render(0) 逐像素比较（循环的下一帧就是第 0 帧），开关运动模糊各一次
  2. 动作连续性：关掉运动模糊，把接缝前后各一帧的范围按 1/4 帧的步长取样，看相邻样本的画面变化量（灰度平均绝对差）；
     片内均匀取 12 处，同样的步长，同样取 2 帧范围，每处取最大一步，再取这 12 个值的中位数作为「片内典型动作」。
     接缝处最大的一步不超过典型值的 3 倍（再加 0.05 噪声余量）才算无缝。
     原理：平滑的运动在细步长下每一步的变化都很小；位置跳变或元素在接缝处突然出现 / 消失，会在某一步里一次变完，比典型动作大一个数量级。
     这是个启发式：片内本来就有硬切或元素突现时，接缝处同样的突现也会被放过；报「有跳变」时用 stills.py 看最后一帧和第 0 帧再判断。
  3. 打印开着运动模糊时接缝前后的帧间变化量，供参考。
不通过时，先看是不是有元素的值没有首尾相接（用 springTo / 线性进度 / 只在某一拍后才出现的元素，到片尾没有归位）；弹簧叠加改用 springLoop。
不支持开 shader 背景的循环片：这里不按时间顺序取帧，而 shader 背景是按时间往前走的。
"""
import io, sys
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from common import serve, open_page, timeline, pop_format, project

ARGV = sys.argv[1:]
FMT = pop_format(ARGV)[0]
cfg = project(); TL = timeline(); FPS = TL.get('fps', cfg.get('fps', 60)); TOTAL = TL['total']; N = round(TOTAL * FPS)
if not cfg.get('loop'): sys.exit('project.json 没有 "loop": true：先写上，运动模糊的子帧才会越过首尾')
if (cfg.get('background') or {}).get('preset'): print('!! 开了 shader 背景：本工具不按时间顺序取帧，结果可能不准')
if N < 16: sys.exit('片子太短（不足 16 帧），无法取样')
STEP = 4                                                    # 每帧取 4 个样本


def grab(pg, f):
    """f 是帧序号（可以是小数）；按 total 取模由 render 完成"""
    pg.evaluate(f'render({f / FPS})')
    return np.asarray(Image.open(io.BytesIO(pg.screenshot())).convert('L'), float)


def steps(pg, f0, frames=2):
    """从帧 f0 起，每 1/STEP 帧取一个样本，共 frames 帧；返回相邻样本的变化量列表"""
    fr = [grab(pg, f0 + j / STEP) for j in range(frames * STEP + 1)]
    return [float(np.abs(fr[j + 1] - fr[j]).mean()) for j in range(len(fr) - 1)]


ok = True
with sync_playwright() as p, serve() as url:
    h, pg, errs = open_page(p, url, FMT, scale=0.5)
    for mb in (True, False):
        pg.evaluate(f'window.__MB_OFF = {str(not mb).lower()}')
        d = np.abs(grab(pg, N) - grab(pg, 0))
        print(f'运动模糊{"开" if mb else "关"}：render(total) 与 render(0) 最大差 {d.max():.1f}，平均差 {d.mean():.4f}')
        ok &= bool(d.max() < 1.0)
        if mb:
            f = [grab(pg, k) for k in (N - 2, N - 1, 0, 1)]
            print('  接缝前后帧间变化量（前 | 接缝 | 后）：' + ' | '.join(f'{float(np.abs(f[i + 1] - f[i]).mean()):.3f}' for i in range(3)))
    seam = steps(pg, N - 1); ks = sorted({int(x) for x in np.linspace(2, N - 4, 12)}); inner = [max(steps(pg, k)) for k in ks]
    lim = np.median(inner) * 3 + 0.05; good = max(seam) <= lim
    print(f'动作连续性（关运动模糊，1/{STEP} 帧步长）：接缝处各步变化量 ' + ' '.join(f'{v:.3f}' for v in seam))
    print(f'  接缝最大 {max(seam):.3f}；片内 12 处各自的最大值：中位 {np.median(inner):.3f}，最大 {max(inner):.3f}；上限（中位 × 3 + 0.05）{lim:.3f} → '
          + ('无缝' if good else '有跳变嫌疑：接缝处某一步的变化远大于片内典型动作'))
    ok &= good
    if errs: print(errs[:3])
    h.close()
print('结论：' + ('可以无缝循环' if ok else '接缝有问题，见上面标出的项'))
sys.exit(0 if ok else 1)
