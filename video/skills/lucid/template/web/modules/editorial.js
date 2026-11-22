/* =========================================================
   modules/editorial.js —— 可选版式之一「报刊社论式的会动的分析图」，适合调研汇报类讲解片
   启用：project.json 的 "modules": ["editorial"]。不是讲解片的默认版式：片子的版式按内容定，只有调研、方案汇报这类
   需要章节导航、引语和数据页的长片才考虑它；短片、宣传片用它会像幻灯片。
   提供：暖白纸面 + 颗粒、左上章节标记、底部分段进度条（PROJECT.parts）、统一角色（人形 / 主角圆点 / 任务方块）、
         引语、启示页、事实条目、产品抬头。版面数字按 1080p 横版写，其他画幅乘 U。
   ========================================================= */
'use strict';
Object.assign(COL, { paper: '#F1EEE7', panel: '#E7E2D7', ink: '#1B1A18', ink2: '#56524B', gray: '#A49F94', rule: '#D3CDBF', red: '#DE4B2D', redDeep: '#B9381F' },
  { bg: '#F1EEE7', acc: '#DE4B2D' }, TH.colors || {});
Object.assign(FONT, { display: 'Songti SC', body: 'PingFang SC', mono: 'JetBrains Mono', serif: 'Instrument Serif' }, TH.fonts || {});
Object.assign(F, {
  song: (s, w = 900) => `${w} ${s}px ${_ff(FONT.display)}`,
  sans: (s, w = 600) => `${w} ${s}px ${_ff(FONT.body)}`,
  mono: (s, w = 400) => `${w} ${s}px ${_ff(FONT.mono)}`,
  serif: (s, it = true) => `${it ? 'italic ' : ''}400 ${s}px ${_ff(FONT.serif)}`,
});
const ED = Object.assign({ furniture: true, grain: 0.06, edgeFade: true }, PROJECT.editorial || {});

// 文字出画淡出：按当前变换算出屏幕位置，左边缘出画或压到章节标记区时变透明。设计上要贴边放字时传 noEdge 或把 editorial.edgeFade 设为 false
function edgeA(xl, yt, ctx) {
  if (!ED.edgeFade) return 1;
  const m = (ctx || CTX).getTransform(), sx = m.a * xl + m.c * yt + m.e, sy = m.b * xl + m.d * yt + m.f;
  return clamp((sx - 10) / 50) * clamp((sy - 84 * U) / 30);
}
const camSet = (ctx, cx, cy, z) => cam(ctx, cx, cy, z);
const camAt = (keys, t) => camKeys(keys, t, E.inOut5);
function etxt(ctx, s, x, y, o = {}) {
  ctx.save(); ctx.font = o.font || F.sans(40); ctx.fillStyle = o.color || COL.ink; ctx.globalAlpha *= (o.alpha ?? 1);
  ctx.textAlign = o.align || 'left'; ctx.textBaseline = o.base || 'alphabetic'; ctx.letterSpacing = (o.ls || 0) + 'px';
  if (!o.noEdge) { const w = ctx.measureText(s).width, sz = fsize(ctx.font); ctx.globalAlpha *= edgeA(o.align === 'center' ? x - w / 2 : o.align === 'right' ? x - w : x, y - sz * 0.85, ctx); }
  ctx.fillText(s, x, y); ctx.restore();
}
// 逐字升起（宋体默认），t 为距出字开始的秒数
function riseText(ctx, s, x, y, t, o = {}) {
  const font = o.font || F.song(96), size = o.size || fsize(font);
  const g = glyphX(s, font, o.ls || 0), x0 = _x0(g, x, o.align);
  ctx.save(); if (!o.noEdge) ctx.globalAlpha *= edgeA(x0, y - size * 0.85, ctx);
  const w = riseLine(ctx, s, x, y, t, Object.assign({ font, size, stagger: o.stagger ?? 0.035, f: 1.6, z: 0.78 }, o));
  ctx.restore(); return w;
}
function tag(ctx, s, x, y, a = 1, o = {}) {
  ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = o.color || COL.red; ctx.fillRect(x, y - 9 * U, 28 * U * (o.rule ?? 1), 3 * U);
  etxt(ctx, s, x + 40 * U, y, { font: F.mono((o.size || 26) * U, 600), color: o.tcolor || COL.ink2, ls: 2, noEdge: o.furn }); ctx.restore();
}
// 统一角色：同一个角色在每个镜头里长得一样
function person(ctx, x, y, s, o = {}) {
  ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1); ctx.fillStyle = o.color || COL.ink;
  ctx.beginPath(); ctx.arc(x, y - s * 0.36, s * 0.2, 0, Math.PI * 2); ctx.fill();
  const bw = s * 0.36, bt = y - s * 0.1, bb = y + s * 0.32;
  ctx.beginPath(); ctx.moveTo(x - bw, bb); ctx.lineTo(x - bw, bt + bw * 0.9); ctx.arc(x, bt + bw * 0.9, bw, Math.PI, 0); ctx.lineTo(x + bw, bb); ctx.closePath(); ctx.fill();
  if (o.label) etxt(ctx, o.label, x, bb + s * 0.38, { font: F.sans(o.lsize || Math.max(26, s * 0.22), 600), align: 'center', color: o.lcolor || COL.ink });
  ctx.restore();
}
function agent(ctx, x, y, r, t, o = {}) {
  const P2 = BEAT * 2;
  ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1);
  const ph_ = (((t - (o.phase || 0)) % P2) + P2) % P2 / P2;
  if (o.pulse !== false) { ctx.save(); ctx.strokeStyle = COL.red; ctx.lineWidth = Math.max(1.5, r * 0.06); ctx.globalAlpha *= (1 - ph_) * 0.45; ctx.beginPath(); ctx.arc(x, y, r * (1.25 + ph_ * 1.6), 0, Math.PI * 2); ctx.stroke(); ctx.restore(); }
  ctx.save(); ctx.strokeStyle = COL.red; ctx.lineWidth = Math.max(1.5, r * 0.08); ctx.globalAlpha *= 0.55; ctx.beginPath(); ctx.arc(x, y, r * 1.38, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  ctx.fillStyle = o.hollow ? COL.paper : COL.red; ctx.strokeStyle = COL.red; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  if (o.hollow) { ctx.lineWidth = r * 0.16; ctx.stroke(); }
  if (o.label) etxt(ctx, o.label, x, y + r * 1.38 + (o.lgap || 46), { font: o.lfont || F.sans(30, 600), align: 'center', color: o.lcolor || COL.red });
  ctx.restore();
}
function taskBox(ctx, x, y, s, o = {}) { ctx.save(); ctx.globalAlpha *= (o.alpha ?? 1); ctx.strokeStyle = o.color || COL.gray; ctx.lineWidth = o.lw || 3; ctx.strokeRect(x - s / 2, y - s / 2, s, s); ctx.restore(); }
function cross(ctx, x, y, s, a, col) { if (a <= 0) return; ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = col || COL.red; ctx.lineWidth = s * 0.28; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x - s / 2, y - s / 2); ctx.lineTo(x + s / 2, y + s / 2); ctx.moveTo(x + s / 2, y - s / 2); ctx.lineTo(x - s / 2, y + s / 2); ctx.stroke(); ctx.restore(); }
function tick(ctx, x, y, s, u, col) { drawPath(ctx, [[x - s * 0.5, y], [x - s * 0.12, y + s * 0.36], [x + s * 0.55, y - s * 0.42]], u, { color: col || COL.ink, lw: s * 0.2 }); }
// 产品抬头：斜体产品名 + 朱红短线 + 元信息
function productHead(ctx, name, meta, t, o = {}) {
  const x = o.x ?? 120, y = o.y ?? 330, sz = o.size || 200;
  const ga = edgeA(x, y - sz * 0.8, ctx); if (ga <= 0) return;
  ctx.save(); ctx.globalAlpha *= ga;
  riseText(ctx, name, x - 6, y, t, { font: F.serif(sz), size: sz, stagger: 0.06, noEdge: true });
  const a = E.out3(prog(t, 0.5, 0.6));
  ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = COL.red; ctx.fillRect(x, y + 40 + (o.my || 0), 56 * a, 4); ctx.restore();
  etxt(ctx, meta, x + 72, y + 52 + (o.my || 0), { font: F.mono(24, 600), color: COL.ink2, ls: 2, alpha: a, noEdge: true });
  ctx.restore();
}
function facts(ctx, list, x, y0, gap, times, t, size = 40) {
  list.forEach((s, i) => {
    const lt = t - times[i]; if (lt <= 0) return;
    const u = E.out3(clamp(lt / 0.5));
    ctx.save(); ctx.globalAlpha *= u * edgeA(x, y0 + i * gap - size, ctx); ctx.fillStyle = COL.red; ctx.fillRect(x, y0 + i * gap - size * 0.36, 12, 12); ctx.restore();
    riseText(ctx, s, x + 32, y0 + i * gap, lt, { font: F.sans(size, 600), size, stagger: 0.025 });
  });
}
// 引语：lines = [[文字, 出现时刻, 着色区间?], ...]
function quote(ctx, lines, x, y, t, o = {}) {
  const sz = o.size || 64, lh = o.lh || sz * 1.42, a0 = lines[0][1], bu = E.out3(prog(t, a0 - 0.2, 0.6));
  if (bu > 0) { ctx.save(); ctx.globalAlpha *= edgeA(x, y - sz, ctx); ctx.fillStyle = COL.red; ctx.fillRect(x, y - sz * 0.92, 6, ((lines.length - 1) * lh + sz * 1.15) * bu); ctx.restore(); }
  lines.forEach(([s, ta, cr], i) => { if (t > ta) riseText(ctx, s, x + 44, y + i * lh, t - ta, { font: F.song(sz, o.weight || 700), size: sz, stagger: 0.022, colors: cr ? colorRange(s, cr) : null }); });
  if (o.by) etxt(ctx, o.by, x + 44, y + (lines.length - 1) * lh + sz * 0.6 + 52, { font: F.sans(28, 500), color: COL.ink2, alpha: E.out3(prog(t, o.byT ?? a0 + 0.6, 0.6)) });
}
function insight(ctx, t, S, label, lines, o = {}) {
  cam(ctx, ...camKeys([[S.t0, 960, 540, 1.0], [S.t1, 960, 540, 1.035]], t));
  const sz = o.size || 104, x = 150, y0 = o.y ?? 470, a = E.out3(prog(t, lines[0][1] - 0.6, 0.5));
  tag(ctx, label, x, y0 - 170, a, { size: 26 });
  lines.forEach(([s, ta, cr], i) => { if (t > ta) riseText(ctx, s, x, y0 + i * sz * 1.42, t - ta, { font: F.song(sz), size: sz, colors: cr ? colorRange(s, cr) : null }); });
  if (o.glyph) o.glyph(ctx, t);
}
function question(ctx, t, S, lines, o = {}) {
  const sz = o.size || 112, x = o.x ?? 150, y0 = o.y ?? 470;
  lines.forEach(([s, ta, cr], i) => { if (t > ta) riseText(ctx, s, x, y0 + i * sz * 1.4, t - ta, { font: F.song(sz), size: sz, colors: cr ? colorRange(s, cr) : null }); });
}
const songW = (s, sz) => measure(s, F.song(sz));

// ---------------------------------------------------------------- 背景与版面（main.js 通过 STYLE 调用）
const PARTS = (PROJECT.parts || []).map(p => [p.label, p.id]);
const PART_OF = {}, CH_LABEL = {};
(PROJECT.chapters || []).forEach(c => { PART_OF[c.id] = c.part; CH_LABEL[c.id] = c.label; });
const _partSpan = {};
(TL.chapters || []).forEach(c => { const p = PART_OF[c.id]; if (!p) return; _partSpan[p] = _partSpan[p] || [c.t0, c.t1]; _partSpan[p][1] = c.t1; });
let _EGRAIN = null;
window.STYLE = {
  background(ctx, t) { fillBg(ctx, COL.paper); },
  overlay(ctx, t, S) {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (ED.grain > 0) {
      if (!_EGRAIN) { _EGRAIN = document.createElement('canvas'); _EGRAIN.width = _EGRAIN.height = 640; const g = _EGRAIN.getContext('2d'), im = g.createImageData(640, 640), r = rng(PROJECT.seed || 1); for (let i = 0; i < im.data.length; i += 4) { const v = 120 + r() * 135; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); }
      const k = Math.floor(t * 12), r = rng(k * 7919 + 13), ox = Math.floor(r() * 640), oy = Math.floor(r() * 640);
      ctx.save(); ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = ED.grain;
      for (let x = -ox; x < W; x += 640) for (let y = -oy; y < H; y += 640) ctx.drawImage(_EGRAIN, x, y);
      ctx.restore();
    }
    if (!ED.furniture || !PARTS.length || !S) return;
    const part = PART_OF[S.chapter], sp = _partSpan[part]; if (!sp) return;
    const a = S.id === Object.values(TL.scenes).sort((x, y) => x.t0 - y.t0)[0].id ? prog(t, 1.0, 1.0) : 1;
    if (CH_LABEL[S.chapter]) tag(ctx, CH_LABEL[S.chapter], 120 * U, 92 * U, a, { furn: true });
    const y = H - 64 * U, x0 = 120 * U, x1 = W - 120 * U, gap = 18 * U, n = PARTS.length, w = (x1 - x0 - gap * (n - 1)) / n, p = (t - sp[0]) / (sp[1] - sp[0]);
    ctx.save(); ctx.globalAlpha *= a * 0.9;
    for (let i = 0; i < n; i++) {
      const x = x0 + i * (w + gap), cur = PARTS[i][1] === part;
      ctx.fillStyle = COL.rule; ctx.fillRect(x, y, w, 2);
      if (cur) { ctx.fillStyle = COL.red; ctx.fillRect(x, y - 1, w * clamp(p), 4); }
      else if (PARTS.findIndex(q => q[1] === part) > i) { ctx.fillStyle = COL.ink2; ctx.fillRect(x, y, w, 2); }
      etxt(ctx, PARTS[i][0], x, y + 32 * U, { font: F.sans(24 * U, cur ? 600 : 400), color: cur ? COL.ink : COL.gray, ls: 1, noEdge: true });
    }
    ctx.restore();
  },
};
