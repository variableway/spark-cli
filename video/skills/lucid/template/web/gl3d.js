/* =========================================================
   gl3d.js —— 透视 3D 卡片（WebGL2），合成进 2D 画布
   Canvas 2D 只有仿射变换，做不出透视倾斜、翻牌、斜着推近的 UI 卡片。这里用离屏 WebGL2 画带透视的贴图四边形，
   再按包围盒贴回主画布；主画布当前的变换（cam、震动、转场位移）会作用在投影后的屏幕坐标上。
   第一次调用 GL3D.card 时才创建 WebGL 上下文，不用就没有开销。

   GL3D.card(ctx, c)  c = {
     img: 'shot_app' 或 Image/Canvas,  x, y: 卡片中心（世界坐标，z=0 平面上 1:1 像素）,  z: 远离镜头为正,
     w, h: 尺寸,  rx, ry, rz: 旋转角度（rx>0 顶边远离，ry>0 右边远离）,  r: 圆角,  a: 透明度,
     dim: 压暗 0..1,  border: 描边亮度,  sheen: 高光强度,  sheenPos: 高光位置（-1..2 扫过）,
     shadow: 阴影强度,  glow: 外发光强度,  glowColor,  vp: [x,y] 消失点（默认画面中心）,
     sub: [u0,v0,u1,v1] 把 img 整张贴到卡片的这块子区域上（卡片其余参数与底图相同）。推近时用它把高清局部截图
          精确叠在原截图对应的位置：底图画一次，高清局部用同样的 x/y/w/h/r* 加 sub 再画一次
   }
   GL3D.uv(ctx, c, u, v) → 卡片上 (u,v) 点此刻的屏幕坐标（让 2D 元素钉在卡片上）

   img 传离屏 Canvas（自己画的界面、appWindow 的结果）时：
   · Canvas 要在 window.INIT 里画好（或第一次用之前画好），再传给 card。每次 card 调用都会把它重新上传成纹理：内容可以逐帧变，
     代价是每次上传一整张贴图；画布大、同一帧里多次调用时明显变慢。
   · 内容不变的 Canvas 设 c.static = true：只在第一次上传，之后复用纹理。appWindow 返回的 Canvas 已经设好。设了 static 之后再改画布内容不会更新。
   · Canvas 不能是 0 宽高；画完以后不要再改它的 width / height（改尺寸会清空画布）。
   ========================================================= */
'use strict';
const GL3D = (() => {
  let gl = null, cv = null, U_ = {}, TEX = new Map();
  const FOCAL = 1800 * U;
  function init() {
    cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    gl = cv.getContext('webgl2', { premultipliedAlpha: true, preserveDrawingBuffer: true, antialias: true, alpha: true });
    if (!gl) throw new Error('WebGL2 不可用');
    const VS = `#version 300 es
    in vec4 aP; in vec2 aUV; out vec2 vUV; void main(){ vUV = aUV; gl_Position = aP; }`;
    const FS = `#version 300 es
    precision highp float; in vec2 vUV; out vec4 o;
    uniform sampler2D T; uniform vec2 S; uniform float R, A, DIM, BORDER, SHEEN, SHEENPOS;
    float sdRR(vec2 p, vec2 b, float r){ vec2 q = abs(p) - b + r; return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r; }
    void main(){
      vec2 p = vUV * S; float d = sdRR(p - S * .5, S * .5, R);
      float aa = max(fwidth(d), 1e-3); float m = 1. - smoothstep(-aa, aa, d);
      vec4 c = texture(T, vUV); c.rgb *= (1. - DIM);
      float s = exp(-pow((vUV.x * .8 + vUV.y * .45 - SHEENPOS) * 7., 2.)) * SHEEN; c.rgb += vec3(s) * c.a;
      float rim = (1. - smoothstep(0., 2.2, -d)) * BORDER; c.rgb += vec3(rim) * c.a;
      o = c * m * A;
    }`;
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const prg = gl.createProgram(); gl.attachShader(prg, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prg, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prg);
    if (!gl.getProgramParameter(prg, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prg));
    gl.useProgram(prg);
    ['T', 'S', 'R', 'A', 'DIM', 'BORDER', 'SHEEN', 'SHEENPOS'].forEach(k => U_[k] = gl.getUniformLocation(prg, k));
    gl.uniform1i(U_.T, 0);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    const aP = gl.getAttribLocation(prg, 'aP'), aUV = gl.getAttribLocation(prg, 'aUV');
    gl.enableVertexAttribArray(aP); gl.enableVertexAttribArray(aUV);
    gl.vertexAttribPointer(aP, 4, gl.FLOAT, false, 24, 0); gl.vertexAttribPointer(aUV, 2, gl.FLOAT, false, 24, 16);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }
  function texOf(src) {
    let t = TEX.get(src);
    if (t && (typeof src === 'string' || src.static)) return t;                    // IMG 里的名字、标了 static 的 Canvas：只上传一次
    const im = typeof src === 'string' ? IMG[src] : src; if (!im) throw new Error('GL3D 没有这张图：' + src);
    if (!t) { t = gl.createTexture(); TEX.set(src, t); }
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, im);   // 传 Canvas 且没标 static 时，每次调用都重新上传（内容可能变了）
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const ani = gl.getExtension('EXT_texture_filter_anisotropic'); if (ani) gl.texParameterf(gl.TEXTURE_2D, ani.TEXTURE_MAX_ANISOTROPY_EXT, 8);
    return t;
  }
  const D2R = Math.PI / 180;
  function world(c, u, v) {
    if (c.sub) { u = lerp(c.sub[0], c.sub[2], u); v = lerp(c.sub[1], c.sub[3], v); }
    const px = (u - .5) * c.w, py = (v - .5) * c.h, pz = 0;
    const rz = (c.rz || 0) * D2R, rx = (c.rx || 0) * D2R, ry = (c.ry || 0) * D2R;
    const x1 = px * Math.cos(rz) - py * Math.sin(rz), y1 = px * Math.sin(rz) + py * Math.cos(rz), z1 = pz;
    const y2 = y1 * Math.cos(rx) - z1 * Math.sin(rx), z2 = y1 * Math.sin(rx) + z1 * Math.cos(rx), x2 = x1;
    const x3 = x2 * Math.cos(ry) + z2 * Math.sin(ry), z3 = -x2 * Math.sin(ry) + z2 * Math.cos(ry), y3 = y2;
    return [c.x + x3, c.y + y3, (c.z || 0) - z3];
  }
  function proj(c, P, m) {
    const vp = c.vp || [W / 2, H / 2], k = FOCAL / Math.max(1, FOCAL + P[2]);
    const sx = vp[0] + (P[0] - vp[0]) * k, sy = vp[1] + (P[1] - vp[1]) * k;
    return [m.a * sx + m.c * sy + m.e, m.b * sx + m.d * sy + m.f, 1 / k];
  }
  const uv = (ctx, c, u, v) => { const p = proj(c, world(c, u, v), ctx.getTransform()); return [p[0], p[1]]; };
  const quad = (ctx, c) => { const m = ctx.getTransform(); return [[0, 0], [1, 0], [1, 1], [0, 1]].map(([u, v]) => proj(c, world(c, u, v), m)); };
  function outline(ctx, q, color, blur, oy, sc) {
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.shadowColor = color; ctx.shadowBlur = blur * sc; ctx.shadowOffsetX = 20000; ctx.shadowOffsetY = oy * sc;
    ctx.beginPath(); q.forEach((p, i) => i ? ctx.lineTo(p[0] - 20000, p[1]) : ctx.moveTo(p[0] - 20000, p[1])); ctx.closePath();
    ctx.fillStyle = '#000'; ctx.fill(); ctx.restore();
  }
  function card(ctx, c) {
    if (!gl) init();
    const a = (c.a ?? 1) * ctx.globalAlpha; if (a <= 0.002) return;
    const q = quad(ctx, c); if (q.some(p => p[2] <= 0)) return;
    const xs = q.map(p => p[0]), ys = q.map(p => p[1]);
    const bx = Math.floor(Math.max(0, Math.min(...xs) - 4)), by = Math.floor(Math.max(0, Math.min(...ys) - 4));
    const bx1 = Math.ceil(Math.min(W, Math.max(...xs) + 4)), by1 = Math.ceil(Math.min(H, Math.max(...ys) + 4));
    if (bx1 <= bx || by1 <= by) return;
    const m = ctx.getTransform(), sc = Math.hypot(m.a, m.b);
    if (c.shadow) outline(ctx, q, `rgba(0,0,0,${0.6 * c.shadow * a})`, 70 * U, 40 * U, sc);
    if (c.glow) outline(ctx, q, c.glowColor || hexA(COL.acc, 0.7 * c.glow * a), 90 * U, 0, sc);
    const data = new Float32Array(36), V = [[0, 0], [1, 0], [1, 1], [0, 0], [1, 1], [0, 1]];
    V.forEach(([u, v], i) => { const p = q[u === 0 ? (v === 0 ? 0 : 3) : (v === 0 ? 1 : 2)], w = p[2]; data.set([(p[0] / W * 2 - 1) * w, (1 - p[1] / H * 2) * w, 0, w, u, v], i * 6); });
    gl.viewport(0, 0, W, H); gl.enable(gl.SCISSOR_TEST); gl.scissor(bx, H - by1, bx1 - bx, by1 - by);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texOf(c.img));
    const sw = c.sub ? c.w * (c.sub[2] - c.sub[0]) : c.w, shh = c.sub ? c.h * (c.sub[3] - c.sub[1]) : c.h;
    gl.uniform2f(U_.S, sw, shh); gl.uniform1f(U_.R, c.r || 0); gl.uniform1f(U_.A, a); gl.uniform1f(U_.DIM, c.dim || 0);
    gl.uniform1f(U_.BORDER, c.border ?? 0); gl.uniform1f(U_.SHEEN, c.sheen || 0); gl.uniform1f(U_.SHEENPOS, c.sheenPos ?? -1);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1;
    ctx.drawImage(cv, bx, by, bx1 - bx, by1 - by, bx, by, bx1 - bx, by1 - by);
    ctx.restore();
  }
  return { card, uv, quad, world, get FOCAL() { return FOCAL; } };
})();
