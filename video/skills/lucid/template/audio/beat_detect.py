"""估计歌曲的 BPM 和第一拍时刻：python3 audio/beat_detect.py 歌曲路径 [--bpm-range 70 180] [--out audio/checks/beats.jpg]
用于 music.source=file：把打印出来的 timeline.bpm / timeline.offset 粘进 project.json，再看拍点网格图核对。
方法：低频到中频的谱通量（onset 包络）→ 自相关找周期（BPM）→ 在该周期的网格上用卷积找相位（第一拍），只用 numpy / scipy。
注意：估计的是稳定节拍的歌（电子、流行、说唱）；有节奏漂移或自由节拍的歌要看图手动调 offset。"""
import argparse, os, subprocess, sys
import numpy as np
from scipy.signal import stft, find_peaks, butter, sosfilt
from scipy.ndimage import uniform_filter1d

ap = argparse.ArgumentParser(); ap.add_argument('song'); ap.add_argument('--bpm-range', nargs=2, type=float, default=[70, 180]); ap.add_argument('--out', default=None)
a = ap.parse_args(); SR = 22050
import imageio_ffmpeg
raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', a.song, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(np.float64)
if len(x) < SR * 4: sys.exit('歌曲太短或读不出来（至少 4 秒）')

# ---------------------------------------------------------------- onset 包络：对数幅度谱的正向差分，低频（底鼓）加权
HOP = 256; f, t, Z = stft(x, SR, nperseg=1024, noverlap=1024 - HOP); S = np.log1p(30 * np.abs(Z))
d = np.maximum(0, np.diff(S, axis=1)); wt = np.where(f < 200, 2.0, np.where(f < 4000, 1.0, 0.5))[:, None]
low = d[f < 150].sum(0); env = (d * wt).sum(0); env = np.maximum(0, env - uniform_filter1d(env, 43)); env /= env.max() + 1e-9; fr = SR / HOP    # 每秒帧数
low = np.maximum(0, low - uniform_filter1d(low, 43)); low /= low.max() + 1e-9      # 只看 150Hz 以下的 onset（底鼓），用来判断哪一拍是小节第 1 拍

# ---------------------------------------------------------------- 周期：自相关，对 BPM 做对数先验（偏向 90–160）避免倍频
ac = np.correlate(env, env, 'full')[len(env) - 1:]; ac /= ac[0] + 1e-9
bpms = np.arange(a.bpm_range[0], a.bpm_range[1] + 0.01, 0.1); score = np.zeros(len(bpms))
for i, b in enumerate(bpms):
    lag = 60 / b * fr; s = 0
    for k, wk in ((1, 1.0), (2, 0.5), (4, 0.25)):                 # 拍、2 拍、4 拍的周期都有峰才算数
        j = lag * k
        if j + 2 < len(ac): s += wk * ac[int(round(j)) - 1:int(round(j)) + 2].max()
    score[i] = s * np.exp(-0.5 * (np.log2(b / 120) / 0.7) ** 2)
pk, _ = find_peaks(score); bpm0 = bpms[pk[np.argmax(score[pk])]] if len(pk) else bpms[np.argmax(score)]
# 精修：在 ±1.5 BPM 内用「整首歌的拍点梳」对齐度打分
def comb(bpm):
    P = 60 / bpm; best = (-1, 0)
    for ph in np.arange(0, P, 0.005):
        ts = np.arange(ph, len(env) / fr, P); idx = np.clip((ts * fr).astype(int), 0, len(env) - 1)
        v = np.maximum.reduce([env[np.clip(idx + o, 0, len(env) - 1)] for o in (-1, 0, 1)]).sum() / len(ts)
        if v > best[0]: best = (v, ph)
    return best
cands = [(comb(b), b) for b in np.arange(bpm0 - 1.5, bpm0 + 1.51, 0.1)]
(v, ph), bpm = max(cands, key=lambda c: c[0][0]); P = 60 / bpm
vi, phi = comb(float(round(bpm)))
if abs(bpm - round(bpm)) < 0.6 and vi >= 0.95 * v: bpm = float(round(bpm)); P = 60 / bpm; ph = phi       # 整数 BPM 吸附（绝大多数歌是整数）：整数的对齐度不低于最优的 95% 就取整数

# ---------------------------------------------------------------- 第一拍：网格相位已知；小节线取每 4 拍里 onset 最强（底鼓）的那一拍；offset 取音乐开始之后的第一条小节线
ts = np.arange(ph, len(env) / fr, P); idx = np.clip((ts * fr).astype(int), 0, len(env) - 1)
strength = np.maximum.reduce([env[np.clip(idx + o, 0, len(env) - 1)] for o in (-1, 0, 1)])
ls = np.maximum.reduce([low[np.clip(idx + o, 0, len(low) - 1)] for o in (-1, 0, 1)]); bar_ph = int(np.argmax([ls[r::4].mean() for r in range(4)])); bar0 = ts[bar_ph]
roll = uniform_filter1d(env, int(0.5 * fr)); t_start = float(np.argmax(roll > 0.15 * roll.mean())) / fr          # 音乐开始的时刻
first = ph + P * np.ceil((t_start - 0.5 * P - ph) / P)                                          # 音乐开始后的第一拍
bar1 = bar0 + 4 * P * np.ceil((t_start - 0.5 * P - bar0) / (4 * P))                              # 音乐开始后的第一条小节线（推断）
first = first + P if first < -0.05 else max(0.0, first)
offset = first
conf = float(np.clip(v / (np.mean(env) + 1e-9) / 6, 0, 1))
print(f'歌曲 {len(x) / SR:.1f}s，音乐约从 {t_start:.2f}s 开始')
print(f'估计 BPM {bpm:g}   第一拍 {first:.3f}s   置信 {"高" if conf > 0.6 else "中" if conf > 0.35 else "低，务必看图"}')
print('粘进 project.json：')
print(f'  "timeline": {{ "mode": "beats", "bpm": {bpm:g}, "offset": {first:.3f}, ... }}')
print(f'  b(n) 是第 n 拍的时刻。BPM 和拍相位通常可靠；哪一拍是小节第 1 拍靠「每 4 拍底鼓最重」推断：推断的小节线在 {bar1:.3f}s，'
      + ('和第一拍一致。' if abs(bar1 - first) < 0.02 else f'比第一拍晚 {round((bar1 - first) / P)} 拍。要让 sections 的小节对齐，就把 offset 改成 {bar1:.3f}（看图确认）。'))
print('检查：细线应当压在鼓点（波形里的尖峰）上；整体偏了就手动微调 offset（每次 ±0.02s）；红线（推断的小节线）错位就加减整拍')

# ---------------------------------------------------------------- 图：波形 + 拍点网格（小节线加粗，红线 = 小节第 1 拍）
from PIL import Image, ImageDraw
W, H = 1600, 260; T = len(x) / SR; out = a.out or os.path.splitext(os.path.basename(a.song))[0] + '_beats.jpg'
if os.path.dirname(out): os.makedirs(os.path.dirname(out), exist_ok=True)
show = min(T, 40.0); n = int(show * SR); cols = W - 60; spp = max(1, n // cols); w = x[:spp * cols].reshape(cols, spp); mx, mn = w.max(1), w.min(1); sc = 90 / (np.abs(x[:n]).max() + 1e-9)
img = Image.new('RGB', (W, H), (250, 248, 242)); dr = ImageDraw.Draw(img); X0 = 30
for i in range(cols): dr.line([(X0 + i, 130 - mx[i] * sc), (X0 + i, 130 - mn[i] * sc)], fill=(60, 66, 76))
k = 0
for t_ in np.arange(first % P, show, P):
    xx = X0 + t_ / show * cols; bar = (round((t_ - bar1) / P) % 4) == 0
    dr.line([(xx, 24), (xx, H - 6)], fill=(214, 70, 50) if bar else (150, 170, 220), width=2 if bar else 1)
for s_ in range(0, int(show) + 1, 2 if show > 20 else 1): dr.text((X0 + s_ / show * cols + 2, 4), f'{s_}s', fill=(70, 70, 80))
dr.text((X0, H - 18), f'BPM {bpm:g}  first beat {first:.3f}s  red = inferred bar line, blue = other beats, first {show:.0f}s', fill=(70, 70, 80))
img.save(out, quality=88); print('拍点网格图：', out)
