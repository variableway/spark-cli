"""检查图与分段频带：模型「看声音」的唯一方式。宽度 1600。
上到下：时间刻度与小节号 → sections / chapter 色带 → 混音波形（红线 = 限幅天花板，红点 = 触顶）→ 底鼓行 → 音效行（名字）→ 各声部 200ms 电平曲线。
竖线：每拍一条细线，小节线（每 4 拍）加粗。"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import uniform_filter1d

SR = 48000; W = 1600; X0, X1 = 52, 1592
COL = {'voice': (130, 60, 170), 'music': (214, 80, 50), 'drums': (36, 100, 200), 'bass': (30, 140, 90), 'sfx': (150, 150, 150)}
SEC_COL = {'intro': (205, 220, 235), 'groove': (205, 232, 205), 'build': (250, 224, 170), 'gap': (60, 60, 60), 'drop': (245, 175, 165),
           'break': (222, 205, 235), 'outro': (190, 228, 226)}
BANDS = [('sub 30-60', 30, 60), ('low 60-120', 60, 120), ('mid 0.8-1.6k', 800, 1600), ('pres 2.5-4k', 2500, 4000), ('air 8-16k', 8000, 16000)]


def font(n):
    try: return ImageFont.load_default(size=n)
    except TypeError: return ImageFont.load_default()


def band_table(mono, secs):
    rows = ['分段频带能量（dB，混音）：'.ljust(18) + ''.join(f'{n:>14s}' for n, _, _ in BANDS)]
    for t0, t1, name in secs:
        x = mono[int(max(0, t0) * SR):int(t1 * SR)]
        if len(x) < 2048: continue
        sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2; fr = np.fft.rfftfreq(len(x), 1 / SR)      # 加窗 FFT，按 Parseval 折算成该频带的均方电平
        rows.append(f'{name[:10]:10s}{t0:5.1f}s'.ljust(18) + ''.join(f'{10 * np.log10(2 * sp[(fr >= a) & (fr < b)].sum() / len(x) ** 2 / 0.375 + 1e-12):14.1f}' for _, a, b in BANDS))
    return '\n'.join(rows) if len(rows) > 1 else ''


def draw(path, mix, stems, TL, offset, beat, secs, events, kicks, typed=True):
    N = mix.shape[1]; TOTAL = N / SR; H = 640; img = Image.new('RGB', (W, H), (250, 248, 242)); d = ImageDraw.Draw(img)
    f1, f2 = font(12), font(10); xs = lambda t: X0 + (X1 - X0) * t / TOTAL
    # 波形 y 40..240
    top, hgt = 58, 190; mid = top + hgt // 2; cols = X1 - X0; spp = max(1, N // cols); mono = mix.mean(0)[:spp * cols].reshape(cols, spp)
    # 拍点网格（贯穿波形与电平两个区域）
    nb = int((TOTAL - offset) / beat) + 1; bars = (X1 - X0) / max(1, nb / 4) >= 34
    for k in range(-int(offset / beat) - 1, nb + 1):
        t = offset + k * beat
        if not 0 <= t <= TOTAL: continue
        bar = k % 4 == 0; x = xs(t)
        if bar or nb <= 160:
            for y0, y1 in ((top, top + hgt), (352, H - 14)): d.line([(x, y0), (x, y1)], fill=(120, 120, 130) if bar else (222, 220, 214), width=2 if bar else 1)
        if bar and bars and k >= 0: d.text((x + 2, 2), f'{k // 4 + 1}', fill=(90, 90, 100), font=f2)
    # 时间刻度
    step = 1 if TOTAL <= 20 else 2 if TOTAL <= 40 else 5 if TOTAL <= 120 else 10
    for t in np.arange(0, TOTAL + 1e-6, step): d.text((xs(t) + 2, 14), f'{t:g}s', fill=(70, 70, 80), font=f1)
    # sections 色带
    for t0, t1, name in secs:
        c = SEC_COL.get(name, (225, 225, 225)) if typed else (228, 226, 220); d.rectangle([xs(max(0, t0)), 30, xs(min(TOTAL, t1)), 54], fill=c, outline=(130, 130, 130))
        d.text((xs(max(0, t0)) + 3, 36), name, fill=(255, 255, 255) if name == 'gap' else (40, 40, 40), font=f1)
    # 混音波形
    mx, mn = mono.max(1), mono.min(1)
    for i in range(cols):
        d.line([(X0 + i, mid - mx[i] * hgt / 2), (X0 + i, mid - mn[i] * hgt / 2)], fill=(30, 36, 44))
        if max(mx[i], -mn[i]) > 0.97: d.line([(X0 + i, top - 3), (X0 + i, top + 2)], fill=(220, 30, 30))
    for s in (-1, 1): d.line([(X0, mid - s * hgt / 2 * 10 ** (-1 / 20)), (X1, mid - s * hgt / 2 * 10 ** (-1 / 20))], fill=(215, 110, 90))
    d.text((4, mid - 6), 'mix', fill=(60, 60, 60), font=f1)
    # 底鼓行、音效行
    d.text((4, 256), 'kick', fill=COL['drums'], font=f1)
    for t in kicks: d.ellipse([xs(t) - 3, 257, xs(t) + 3, 263], fill=(220, 40, 40))
    d.text((4, 284), 'sfx', fill=(90, 90, 90), font=f1)
    for j, (t, name) in enumerate(events):
        x = xs(t); d.line([(x, 272), (x, 346)], fill=(110, 110, 110))
        if len(events) <= 60: d.text((x + 2, 274 + (j % 5) * 14), name[:12], fill=(60, 60, 60), font=f2)
    # 电平曲线
    y0, sc = H - 18, 4.4
    def curve(x, col, wd=2):
        m = x.mean(0) if x.ndim == 2 else x; r = np.sqrt(uniform_filter1d(m ** 2, int(0.2 * SR))[::spp][:cols] + 1e-12); db = np.maximum(20 * np.log10(r), -60)
        d.line([(X0 + i, y0 - (db[i] + 60) * sc) for i in range(len(db))], fill=col, width=wd)
    for yv in (-60, -40, -20, 0): yy = y0 - (yv + 60) * sc; d.line([(X0, yy), (X1, yy)], fill=(214, 210, 200)); d.text((4, yy - 6), f'{yv}dB', fill=(120, 120, 120), font=f2)
    for name, x in stems.items(): curve(x, COL.get(name, (100, 100, 100)))
    curve(mix, (0, 0, 0), 3)
    lx = X0 + 6
    for name in list(stems) + ['mix']:
        c = COL.get(name, (0, 0, 0)); d.rectangle([lx, 356, lx + 10, 366], fill=c); d.text((lx + 14, 354), name, fill=(40, 40, 40), font=f1); lx += 80
    d.text((X1 - 330, 354), '200ms RMS | red line = limiter ceiling | red dot = clipped', fill=(120, 120, 120), font=f2)
    img.save(path, quality=88)
    return band_table(mix.mean(0), secs)
