/* =========================================================
   bg.js —— WebGPU shader 背景层（可选，project.json 的 background.preset 非空时启用）
   基于开源库 shaders（MIT）的 createRendererFromJSON + renderFrame({deltaSeconds})。改动前先看 references/shader-background.md：
   1. 画布要固定 CSS 宽高，不然渲染器会按布局把画布改成一半宽。
   2. 不能在 await renderFrame 之后立刻 drawImage，约一半的帧读到全透明；要用 canvas.toBlob 读回。
   3. delta 不被截断：任意跳到第 t 秒，结果与逐帧累加逐像素一致，所以分段并行渲染是对的。
   4. 时间只能向前。要回到更早的时刻，必须销毁并重建渲染器，再从 0 跳到目标。
   5. 整台机器同时使用 WebGPU 的 Chrome 超过 3 个会互相抢资源，速度掉到几十分之一；render.py 会排队领名额。
   可选：background.veil（0–1，盖一层底色）、background.speed（时间倍率）、background.ranges（只在这些时段画）。
   ========================================================= */
'use strict';
window.BG = { ready: false, on: false, frame: null, t: 0 };
window.bgInit = async function () {
  const cfg = PROJECT.background;
  if (!cfg || !cfg.preset) return;
  const host = document.createElement('div');
  host.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px;overflow:hidden;pointer-events:none;opacity:0`;
  const gl = document.createElement('canvas'); gl.style.cssText = `width:${W}px;height:${H}px`;
  host.appendChild(gl); document.body.appendChild(host);
  const out = document.createElement('canvas'); out.width = W; out.height = H;
  const o2 = out.getContext('2d');
  const mod = await import(cfg.module || './vendor/shaders-core.js');
  let r = null, clock = 0;
  async function build() {
    if (r) { try { r.dispose(); } catch (e) {} }
    r = mod.createRendererFromJSON({ components: cfg.preset });
    await r.initialize(gl);
    if (r.getFailureReason && r.getFailureReason()) throw new Error('WebGPU 不可用：' + r.getFailureReason());
    clock = 0;
  }
  await build();
  window.BG.frame = out; window.BG.ready = true;
  const ranges = cfg.ranges || null;                         // [[起秒, 止秒], ...]：只在这些时段画 shader，其余时段不渲染、不读回
  window.bgAt = async function (t) {
    window.BG.on = !ranges || ranges.some(([a, z]) => t >= a && t < z);
    if (!window.BG.on) return;
    t = Math.max(0, t) * (cfg.speed ?? 1);
    if (t < clock - 1e-6) await build();
    const d = t - clock;
    await r.renderFrame({ deltaSeconds: d > 0 ? d : 0, waitForGpu: false }); clock = t;
    const bl = await new Promise(res => gl.toBlob(res, 'image/png'));
    const bm = await createImageBitmap(bl); o2.clearRect(0, 0, W, H); o2.drawImage(bm, 0, 0); bm.close();
    window.BG.t = t;
  };
};
