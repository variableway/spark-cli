# 声音：配乐、音效、混音

声音由 `python3 audio/synth.py` 一次做完：配乐 + 音效 + 人声 + 响度校准，全部从 `project.json` 的 `music`、`timeline.json`、`audio/events.json` 算出来。不用改 `synth.py`。同样的输入和 seed，输出逐字节相同。

你听不到声音。判断靠三样东西：检查图 `audio/checks/wave_mix_small.jpg`、打印的 LUFS 和限幅占比、分段频带表。没看这三样就不要说「声音没问题」。

## 一、选来源和风格

| 片子 | `source` / `style` | 为什么 |
|---|---|---|
| 无旁白的宣传片、产品片、卡点片 | `synth` / `electronic` | 画面靠节拍卡点，电子乐的底鼓、build、drop 最容易让画面动作有「落点」。这是不写 style 时的默认 |
| 产品演示、界面动效、需要平静氛围 | `synth` / `ambient` | 同一套分段，换成钟音琶音，没有踩镲拍手军鼓，不抢画面 |
| 有配音的讲解片 | `synth` / `piano` | 钢琴织体不抢人声，按章节换织体。`timeline.mode` 是 `voice` 时默认用它 |
| 用户给了歌 | `file` | 用用户的歌，音效叠在上面。先跑 `beat_detect.py`，见第五节 |
| 只要点击声、转场声 | `none` | 只有音效。默认响度 -18 LUFS，因为稀疏的音效校到 -14 会被推得过响 |

不要因为「电子乐不会出错」就给讲解片用它。有配音时音乐比人声低约 13 到 17 dB，鼓点多的电子乐在这个电平下只剩一团低频。

## 二、`music` 字段

```json
"music": {
  "source": "synth", "style": "electronic",
  "key": "A minor", "progression": ["Am", "F", "C", "G"], "chord_beats": 4,
  "sections": [
    {"from": 0,  "to": 4,    "type": "intro"},
    {"from": 4,  "to": 12,   "type": "groove"},
    {"from": 12, "to": 15.75,"type": "build"},
    {"from": 15.75, "to": 16, "type": "gap"},
    {"from": 16, "to": 24,   "type": "drop"},
    {"from": 24, "to": 32,   "type": "outro"}
  ],
  "kicks": [[4, 15], [16, 24], [24, 30, 2]],
  "kick_zoom": 0.008, "lufs": -14
}
```

- 拍号都相对 `timeline.offset`，和镜头里的 `b(n)` 是同一个坐标。`from`/`to` 可以是小数。
- `progression` 写和弦名：`Am F C G`、`Em7`、`Cmaj7`、`Dsus4`、`G7`、`Fadd9`。不写则按 `key` 取常用进行（小调 i VI III VII，大调 I V vi IV）。`chord_beats` 是每个和弦的拍数，默认 4。
- `kicks` 的元素是 `[起拍, 止拍, 步长=1]`。**底鼓只放在这些拍上，画面的随拍缩放（`kick_zoom`）读的也是这份表**，所以画面和声音一定同步。没写 `kicks` 就没有底鼓和侧链，合成器会打印提示。底鼓不要跨进 `gap`，那一拍的画面缩放会没有声音。
- `lufs`：有配音默认 -16，无配音默认 -14，true peak 不超过 -1 dBTP。
- 单个 section 可以覆盖该段的任何参数，例如 `{"from":4,"to":8,"type":"groove","arp":0,"level":1.2}`。参数含义见 `audio/score_electronic.py` 开头的 `BASE`。
- `fade_in`、`fade_out`（秒）对配乐生效，默认电子乐淡出 1 秒。落版想让和弦自然余音，把 `fade_out` 调长。
- `piano` 风格读 `key`、`roles`、`heartbeat`、`quiet`、`insights`、`minor_span`，字段说明在 `audio/score_piano.py` 开头。它不读 `progression`、`sections`、`kicks`。

## 三、sections 怎么设计

每种 type 决定哪些声部进场、滤波开合和密度。声音的结构要和画面的叙事同形：

| type | 声音 | 画面该做什么 |
|---|---|---|
| `intro` | 铺底滤波慢慢打开，轻踩镲，次低频涌入 | 钩子：一个问题、一个反常的画面。动作少而干净 |
| `groove` | 琶音、反拍低音、踩镲、2 和 4 拍拍手 | 展示：卡片、功能、数字逐个出现，镜头切点落在拍上 |
| `build` | 琶音渐亮，踩镲渐强，军鼓滚奏越来越密，上升音，整体变薄 | 加速：切得更快，元素越来越多，画面「憋着」 |
| `gap` | 全部静音，混响尾巴也切掉 | 画面也停：最后一个元素定住，或留一帧黑 |
| `drop` | 最满：重底鼓、七把锯齿和弦、十六分低音、主旋律、侧链，起点有镲和次低频下坠 | **全片最大的画面动作放在 drop 的第一拍**：大标题砸入、整屏闪白、镜头猛推 |
| `break` | 铺底加稀疏琶音，没有鼓 | 情绪缓一下，放一句要听清的话 |
| `outro` | 和弦长音按指数衰减，上行玻璃音，起点低频轰鸣 | 落版：品牌标志、行动号召，停留到片尾 |

为什么这样排：观众靠「紧张后释放」感到节奏，`build` 把张力拉满，`gap` 让耳朵和眼睛同时空一下，`drop` 的第一拍把张力放掉。画面动作要落在那一拍上，听感和视觉才是同一个事件。时长参考：15 秒的 128 BPM 片子大约 8 小节，`gap` 取 1/4 拍，`build` 2 到 4 拍起；更长的片子可以重复 `groove`、`build`、`drop`，不要拉长某一段。

没写 `sections` 时，合成器按小节取整，默认分 intro / groove / outro 三段，并打印提示。宣传片要自己写。

## 四、登记音效

在镜头代码里，动作发生的那一帧写 `EV(t, '名字', {…})`，时刻必须来自画面代码里算出的动作时刻，不在别处手写。`dump_events.py` 导出 `audio/events.json`，`synth.py` 渲染。

- **音效放在动作发生的那一帧。** 元素落位的瞬间、点击的瞬间、切镜头的瞬间。提前或延后超过 50 毫秒，观众就会觉得声音和画面是两件事。
- **`t` 永远是动作发生的那一刻，不用自己算提前量。** 每个音效注册时标了对齐方式，`synth.py` 按它自动提前起点（`--list-fx` 在每个名字前打印）：
  - 对准起点：点击、落位、冲击这类瞬态在开头的声音，从 `t` 开始响。
  - 对准峰值：`whoosh`、`swish`、`swoop` 这类划过声，最响的一刻落在 `t`（`whoosh` 的峰值在起点后约 0.4 秒，会自动提前）。
  - 对准结尾：`riser`、`whoosh_in`、`rev_crash`、`rush`、`rise`、`swell` 这类冲向某一刻的声音，结束的那一刻落在 `t`，所以声音在 `t - dur` 就开始了。
  - 同一时刻登记的 `tick` 和 `whoosh`，混音后峰值相差不到 10 毫秒。
  - 个别事件要改对齐方式时写 `{align: 'start' | 'peak' | 'end'}`。
- **不要每个动作都配音效。** 只给观众应该注意的动作配：落位、点击、冲击、转场。连续出现的同类动作（如打字）可以配，音量放小。每个动作都响，声音就成了噪声。
- **冲击要稀。** `impact` 只给全片一两个最大的动作，通常是 `drop` 的第一拍和落版。drop 的起点音乐里已有镲和次低频下坠，`impact` 叠在上面时用 `{size: 0.8}`，否则两次冲击叠加，限幅器会把那一拍压扁。同一拍不要再叠 `boom`、`logo_hit`。
- **`riser` 的 `t` 写它冲向的那个大动作的时刻。** `dur` 是它提前响多久，例如 `EV(b(12), 'riser', {dur: 2})`：从第 12 拍前 2 秒开始升，到第 12 拍结束。
- 名字写错时 `synth.py` 报错并列出全部有效名字，不会静默跳过。通用参数：`v` 音量倍数，`pan` 声像 -1 到 1，`dur` 时长，`n` 序号。

全部音效名和每个的说明、可选参数：`python3 audio/synth.py --list-fx`。分类速查：

- 点击与提示：`tick` `tick_soft` `tick_drop` `tick_run` `click` `clack` `blip` `key`（打字）`shutter`（快门）`pop` `pin` `wood` `node` `step` `pluck` `glitch` `sparkle` `shimmer` `ping` `ping_far` `chime_up` `gate_ok` `bell`
- 冲击与落位：`impact` `boom` `logo_hit` `stab` `num_hit` `stamp` `heavy` `thunk` `low_hit` `land` `car_in` `chord_hit` `fall2` `wheel` `paper`
- 转场与运动：`whoosh` `whip` `swish` `pen` `whoosh_in` `riser` `downlifter` `rev_crash` `swoop` `boundary` `wind` `rush` `rise` `slide` `slide_down` `swell` `blur_swell` `chord_lift` `title_rise` `rails` `car_move`

需要新音效时，在 `audio/instruments.py` 里用 `@fx_('名字', '一句话说明', '可选参数', at='start' | 'peak' | 'end')` 注册一个函数，不要在 `synth.py` 里写分支。`at` 写这个声音的哪一点对准 `t`（默认起点）。

## 五、用户给了歌（`source: "file"`）

```bash
python3 audio/beat_detect.py assets/song.mp3 --out audio/checks/beats.jpg
```

输出 BPM、第一拍时刻，以及可直接粘进 `project.json` 的 `timeline.bpm` 和 `timeline.offset`，并画一张带拍点网格的波形图。细线应当压在鼓点上；整体偏了就把 `offset` 微调 0.02 秒。BPM 和拍相位通常可靠，「哪一拍是小节第 1 拍」靠推断，四拍都有底鼓的歌容易错，看图判断，错了就把 `offset` 加减整拍。

之后 `sections` 和 `kicks` 照常写，拍号相对 `offset`；`kicks` 要写在歌里真有底鼓的拍上，画面缩放才对得上。`music.file` 是相对项目根的路径，`gain` 是 dB。歌比成片长，合成器在片尾 `fade_out` 秒内淡出；歌比成片短，会打印差几秒。

**用歌中间的一段**：`"start": 秒`，从歌的这一秒开始取，长度是成片时长。例如 `"music": {"source": "file", "file": "assets/song.mp3", "start": 42.5}`。先用 `beat_detect.py` 找到想要的段落起点，起点最好落在一拍上，这样 `timeline.offset` 就是第一拍相对 `start` 的偏移，BPM 不变。`start` 超出歌曲长度会报错。`beat_detect.py` 打印的时刻是相对歌曲开头的，设了 `start` 之后把 `offset` 减去 `start`（取到歌里第一个落在片内的拍）。

**循环片**：`project.json` 里 `"loop": true` 时，合成器把歌里「片尾之后」的 50 毫秒交叉淡入到成片开头，让末尾的声音自然接上开头；这时不做默认的淡入淡出，也不做开头的防爆音渐入。歌曲后面没有多余的 50 毫秒时，用片尾自己的最后 50 毫秒做交叉淡化。如果歌曲本身没有循环感（段落结尾和开头的和弦、节奏对不上），交叉淡化只能消除点击声，不能让它听起来循环；选 `start` 时让片尾落在一个小节边界上。

## 六、看不到声音时怎么检查

1. **检查图** `audio/checks/wave_mix_small.jpg`（1600 像素宽）。从上到下：时间刻度和小节号，sections 色带，混音波形，底鼓行，音效行，各声部电平曲线。拍线每拍一条，小节线加粗。看：
   - 红点（触顶）不应出现；红线是限幅天花板。
   - drop 的波形和电平应明显高于前面各段；`gap` 应是一条平线。
   - 底鼓红点应压在拍线上，且和画面的缩放拍一致。
   - 音效竖线应落在画面动作的时刻，不要全挤在一处。
   - 蓝色（鼓）和红色（音乐）电平在 drop 里应互相让位，呈锯齿状，说明侧链在起作用。
2. **LUFS 和 true peak**。打印的响度应在目标 ±0.3 LU 内，true peak 不高于 -1 dBTP。差得多说明限幅器已经顶住，减少瞬态很强的音效。
3. **限幅/削波动作占比**。限幅只集中在一两处（drop 第一拍、最大的冲击）时，2% 以内是母带正常压住最响的一下，会打印「正常」。分散在多处超过 1%，或集中处超过 2%，会提示「混得太满」并列出时刻。处理办法：不要把 `impact`、`boom`、`logo_hit` 叠在同一拍，给 drop 起点的 `impact` 写 `size: 0.8`，或给那一段的 section 写更低的 `level`。
4. **分段频带表**。看每段的 sub、low、mid、pres、air 电平（dB）：drop 的 sub 和 low 应比 groove 高，`gap` 应接近 -100 dB。参考值：质量较高的 128 BPM 成片，drop 段约为 sub -19、low -19、mid -32、pres -39、air -36。low 比参考低很多，成片会单薄；mid 比参考高很多，低频会被盖住。
5. 有配音时，打印里「音乐在人声段」应比「无人声段」低约 3 到 5 dB，说明人声压低配乐生效；人声段电平比人声低约 13 到 17 dB。

改了 `sections`、`kicks` 或事件后，`render.py` 渲染前会自动重跑 `synth.py`（电子乐 15 秒片子约 2 秒）；只想听声音时单独跑它，再看一次检查图。
