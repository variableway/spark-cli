# shader 背景：什么时候用，怎么用

## 一、先判断要不要用

shader 背景让纸面或舞台有流动的光和质感，但它会抢注意力，也会让渲染变慢、变脆弱。**默认不用。**

同一个工程开和关 shader，在同样的时刻对比，主体画面完全一样，差别只在背景的明暗起伏；开 shader 时网格线这类细节反而更淡。单独渲染时开 shader 只慢约 30%，但整台机器同时有超过 3 个使用 WebGPU 的 Chrome 时，每个进程会掉到 0.2 帧/秒（15 秒的片子从 1 分钟变成半小时以上）。所以只在背景本身就是设计的一部分时才开。

| 场景 | 建议 |
|---|---|
| 讲解、调研汇报、数据密集 | **不用。** 纯色底，文字最清楚 |
| 产品发布、品牌宣传、开场/结尾 | 用，背景承载气质 |
| 只有个别镜头要气氛（开场、片名） | 不开全局背景；在那几个镜头里单独铺一层（见下"局部用法"）或用 Canvas 2D 画渐变 |
| 用户明确要求"炫一点""有设计感的背景" | 用，并用 `veil` 控制可读性 |

## 二、启用

1. `python3 tools/vendor_shaders.py`（一次；从 jsDelivr 取已打包的 ES 模块，约 2.5MB，MIT）。
2. 在 `project.json` 的 `background.preset` 里写组件树：

```json
"background": {
  "veil": 0.0,
  "speed": 0.5,
  "preset": [
    { "type": "MeshGradient", "props": { "stops": [
        {"color": "#F1EEE7", "position": 0}, {"color": "#F4C9B8", "position": 0.8}, {"color": "#DE4B2D", "position": 1} ],
      "drift": 0.6, "variation": 0.5 } },
    { "type": "FilmGrain", "props": { "strength": 0.12, "bias": 1.5 } }
  ]
}
```

- `speed`：时间倍率。0.5 表示背景比画面慢一半，更沉稳。
- `veil`：0–1，在 shader 之上盖一层底色（`theme.colors.bg`）。文字不够清楚时先加 `veil`，不要加粗字。
- 组件是**图层**：先写的在下面；效果类组件（FilmGrain、Blur…）作用于它之前画的所有内容，必须放在生成器之后。

**组件名与 prop 名一律去查，不要凭感觉写**：库的 `skills/shaders/components.md`（一行一个组件）+ 对应 `packages/core/src/shaders/<名>/index.ts`（真实 prop 名、默认值、范围）。MeshGradient 默认色板是紫粉橙，不覆盖 `stops` 就是"AI 渐变"那种模板味。

## 三、结论（headless Chrome，Apple Metal）

这些是做模板时逐条验证的，**改动 `bg.js` 前先看**：

| # | 结论 | 为什么重要 |
|---|---|---|
| 1 | 渲染器的 `renderFrame({deltaSeconds})` 是**帧锁定**的：时钟 = 传入 delta 的累加，不读墙上时钟 | 这是逐帧渲染视频的前提（库 v4.0.2 起提供） |
| 2 | 同一帧在两个独立浏览器里渲染，**逐像素一致** | 并行渲染各段、重渲某一段都安全 |
| 3 | delta **不被截断**：一次跳 60 秒、分 6×10 秒、60×1 秒、240×0.25 秒，与逐帧 3600 步结果完全一致 | 可以直接跳到任意起点；每个并行进程第一次 `render(t)` 就跳到自己的起点 |
| 4 | 步长不影响结果：1/12 秒 ×60 步 = 1/60 秒 ×300 步 | 可以放心用大步长做静帧预览 |
| 5 | **时间只能向前**。回到更早的时刻必须销毁并重建渲染器再跳 | `bg.js` 的 `bgAt` 遇到倒退会自动重建；`stills.py` 的帧按时间升序渲 |
| 6 | 每帧约 1–2 ms（1080p，含读回） | shader 不是性能瓶颈 |

## 四、五个坑

1. **画布必须固定 CSS 宽高。** 不设的话，渲染器按布局把画布改成 960×1080（宽度减半），画面只有左半边有内容。
2. **不能在 `await renderFrame()` 之后立刻 `drawImage`。** 约一半的帧读到全透明（WebGPU 画布的当前纹理已被换掉）。要用 `canvas.toBlob()` → `createImageBitmap()` 读回，它会和 GPU 同步。慢约 40 ms/帧，可接受。
3. **不要用 `requestAnimationFrame` 等一帧再读。** 在 headless 里会读到全空（200 帧里 100%）。
4. **多个 Chrome 同时用 WebGPU 会偶发卡死。** 4 个进程里常有 1 个挂在某一帧，单进程从不挂。`render.py` 每帧有 30 秒看门狗，超时自动杀掉、重开、从那一帧续渲；开 shader 时默认只开 3 个进程，并且整台机器最多 3 个 WebGPU Chrome（用系统临时目录里的文件锁排队）。
5. **Chrome 退出很慢。** shader 逐帧渲染后，正常关闭要等 GPU 资源回收，随帧数增长（240 帧 21 秒，数千帧可达几分钟）。`tools/common.py` 的 `Handle.close()` 直接按临时用户目录 `pkill -9` 这个 Chrome，**只在产物已落盘后调用**。

## 五、局部用法

只有个别镜头要 shader（比如片名页）时，不要开全局背景（它会让整片的每一帧都读回）。做法：

- 写 `"background": {"preset": [...], "ranges": [[0, 3.75], [12, 15]]}`：范围外不渲染 shader、不读回，画面退回 `theme.colors.bg`；
- 或者用 Canvas 2D 画径向渐变（`glow`）加颗粒，视觉相近、没有 GPU 依赖。

## 六、授权与署名

库是 MIT 授权（© Shader Effects, Inc.）。成片里不需要署名；若把 `vendor/shaders-core.js` 随工程分发，保留它自带的许可头。库的设计编辑器、预设库（Pro）有独立条款，本模板不使用。
