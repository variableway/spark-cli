"""配音：
  python3 tools/tts.py probe                 列出各配音后端能不能用，以及 auto 会选哪个
  python3 tools/tts.py voices [--lang zh|en] [--grep 关键词] [--provider mcode|edge]
                                             列出可用音色，一行一个：voice_id、性别和年龄感、一句描述。mcode 读在线音色列表，拿不到时列内置的常用音色；
                                             edge 读 edge-tts 的音色表（需联网）。不写 --provider 时用 auto 选中的后端
  python3 tools/tts.py audition "<一句话>" <voice_id> [<voice_id> ...] [--speed 1.1]
                                             同一句话分别用几个音色合成 → audio/audition/<音色>.mp3，打印每个的时长、语速（字/秒）和自动转写。
                                             zh-CN-XiaoxiaoNeural 这类 edge 音色走 edge，其余走 mcode
  python3 tools/tts.py full [标签] [--no-asr]  整段一次合成（镜头之间用 <#gap#> 停顿标记连接）→ audio/narration_<标签>.mp3/.wav，
                                             并复制为 audio/narration.mp3/.wav；后端能给出词级时间时另存 audio/narration.words.json。
                                             实际用的后端和音色记在 audio/narration.json（deliver.py 读它写「配音」一行）。
                                             合成完有转写后端时自动转写核对（同 asr），直接打印和稿子对不上的英文词、数字、其他词（名字、多音字）；--no-asr 跳过
  python3 tools/tts.py once args.json out.mp3 [--asr]   单次合成试读（短句试读读音；--asr 同时转写）
  python3 tools/tts.py asr [标签|current]     分段转写整段配音，核对英文名与关键词有没有读错 → audio/asr/

音色：没写 voice.voice_id 时按配音稿语言用默认音色，中文 Chinese (Mandarin)_Gentleman（温润男声），英文 English_Trustworthy_Man。
只在另一个声音明显更合适时才换（儿童片、用户点名了语气或性别）：voices 列候选、audition 试读比较，选定后写进 project.json 的
voice.voice_id（edge 写 voice.edge.voice），voice.why 写一句为什么换（deliver.py 抄进交付核对）。vo.json 可写 "lang": "en" 指定语言。

后端写在 project.json 的 voice.provider：
  auto（默认）  依次探测 mcode、edge，用第一个可用的，并打印选了哪个、为什么
  mcode        MiniMax Code 的 mcode-tools 合成（voice_id、speed、emotion 是它的参数）；转写也用它
  edge         edge-tts（pip 包，需联网）。voice.edge = {"voice": "zh-CN-YunxiNeural", "rate": "+0%", "volume": "+0%"}
               整段一次合成，拿到词级边界后在停顿标记处切开、补足停顿时长；词级时间写进 narration.words.json
  file         用户给的录音：voice.file = {"audio": "audio/recording.wav"}（相对工程根目录，任何 ffmpeg 能读的格式）
读音核对（asr）只在 mcode 可用时能做（用它转写，和合成用哪个后端无关）；不可用时会提示「无法自动核对读音」，改为请用户试听。
核对输出三类：英文词（转写里找不到）、数字（阿拉伯数字和中文读法都找不到）、其他对不上的词（逐字比对稿子和转写，多是名字、多音字、同音字），
每条带前后文。全文转写在 audio/asr/<标签>_partN.txt。
mcode 服务偶发 500 / 429 / "temporarily unavailable"：脚本自动等待重试。
"""
import asyncio, difflib, importlib.util, json, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from common import ROOT, project, vo, ffmpeg

SR = 48000
TAGS = r'\((?:breath|chuckle|laughs|sighs)\)'
MARK = r'<#([\d.]+)#>'
AUDIO = ROOT / 'audio'
WORDS = AUDIO / 'narration.words.json'


def script_text(v):
    """整段配音稿：镜头之间用 <#gap#> 连接，再按 tts_fix 换同音字"""
    VO, fix = vo()
    text = f"<#{v.get('gap', 1.4)}#>".join(t for _, t in VO)
    for a, b in fix.items():
        assert a in text, f'tts_fix 里的「{a}」在配音稿里找不到'
        text = text.replace(a, b)
    return text, len(VO)


def to_wav(src, wav):
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', str(src), '-ac', '1', '-ar', str(SR), '-c:a', 'pcm_s16le', str(wav)], check=True)
    return wav


def to_mp3(src, mp3):
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', str(src), '-b:a', '192k', str(mp3)], check=True)
    return mp3


def decode(path):
    import numpy as np
    raw = subprocess.run([ffmpeg(), '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def write_wav(x, wav):
    import numpy as np, scipy.io.wavfile as w
    w.write(str(wav), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


# ================================================================ mcode：MiniMax Code 的 mcode-tools
SC_CALL = ['mcode-tools', 'connector', 'call']
SYNTH_TOOL = 'connector__matrix__synthesize_speech'


def mcode_probe():
    if not shutil.which('mcode-tools'):
        return False, 'PATH 上没有 mcode-tools（不在 MiniMax Code 里运行）'
    try:
        r = subprocess.run(['mcode-tools', 'connector', 'tool', SYNTH_TOOL], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return False, 'mcode-tools 90 秒内没有响应'
    if r.returncode != 0 or SYNTH_TOOL not in r.stdout:
        return False, 'mcode-tools 调用失败：' + (r.stdout + r.stderr).strip().splitlines()[-1][:160] if (r.stdout + r.stderr).strip() else 'mcode-tools 调用失败'
    return True, 'mcode-tools 可用，配音工具在线'


def run_json(cmd, tries=15):
    o = ''
    for k in range(tries):
        r = subprocess.run(cmd, capture_output=True, text=True)
        o = r.stdout + r.stderr
        if 'MCODE_AUTH_PROVIDER' in o or 'unauthorized' in o.lower():
            raise SystemExit('mcode-tools 没有登录或不在 MiniMax Code 里运行，不要重试：' + o.strip()[:200] + '\n  → 把 voice.provider 改成 edge 或 file，或保持 auto。')
        bad = ('服务器繁忙' in o) or ('temporarily unavailable' in o) or ('429' in o and 'rate' in o.lower()) or r.returncode != 0
        if bad:
            print(f'  重试 {k + 1}：{o.strip()[:140]}', flush=True); time.sleep(20); continue
        try:
            return json.loads(r.stdout)
        except Exception:
            print('  输出不是 JSON：', o[:200]); time.sleep(10)
    raise SystemExit('失败：' + o[:300])


def mcode_synth(args_file, out_mp3):
    d = run_json(SC_CALL + [SYNTH_TOOL, '--args-file', str(args_file)])
    if d.get('code') not in (0, None) or not d.get('node_id'):
        raise SystemExit('合成失败：' + json.dumps(d, ensure_ascii=False)[:300])
    u = run_json(['mcode-tools', 'get_asset_url', str(d['node_id'])])['download_url']
    subprocess.run(['curl', '-s', '-L', '-o', str(out_mp3), u], check=True)
    return out_mp3


RECOMMENDED = 'Chinese (Mandarin)_Gentleman'      # 中文片的默认音色（温润男声）
RECOMMENDED_EN = 'English_Trustworthy_Man'         # 英文片的默认音色（英文母语男声）


def script_lang():
    """配音稿的语言：vo.json 写了 "lang" 就用它；否则汉字占字母的两成以上算 zh，其余算 en"""
    try: d = json.load(open(ROOT / 'script' / 'vo.json', encoding='utf-8'))
    except (OSError, ValueError): return 'zh'
    if d.get('lang'): return d['lang'].split('-')[0]
    t = ' '.join(x.get('text', '') for x in d.get('scenes', []))
    cjk = len(re.findall(r'[\u4e00-\u9fff]', t)); lat = len(re.findall(r'[A-Za-z]', t))
    return 'zh' if cjk and cjk >= 0.2 * (cjk + lat) else 'en'


def default_voice():
    return RECOMMENDED_EN if script_lang() == 'en' else RECOMMENDED


def mcode_voice(v):
    if v.get('voice_id'): return v['voice_id']
    d = default_voice()
    print(f'未指定音色，按配音稿语言（{script_lang()}）用默认音色 {d}；只有另一个声音明显更合适时才换（tts.py voices、audition）', flush=True)
    return d


def mcode_full(v, text, tag):
    args = {'text': text, 'voice_id': mcode_voice(v), 'speed': v.get('speed', 1.12), 'output_file': f'narration_{tag}'}
    if v.get('emotion'):
        args['emotion'] = v['emotion']          # 默认不传：让模型自己判断语气，传 happy 会多出怪异的哼声
    af = AUDIO / f'tts_args_{tag}.json'
    json.dump(args, open(af, 'w', encoding='utf-8'), ensure_ascii=False)
    mp3 = mcode_synth(af, AUDIO / f'narration_{tag}.mp3')
    return mp3, to_wav(mp3, AUDIO / f'narration_{tag}.wav'), None


def transcribe(mp3_path, prompt=None):
    if prompt is None:
        prompt = ('Transcribe this English voice-over word for word, keep punctuation, do not rewrite.' if script_lang() == 'en'
                  else '逐字转写这段普通话配音，英文单词按听到的发音写，保留标点，不要改写。')
    up = run_json(['mcode-tools', 'upload_temp_url', str(mp3_path)])
    t = run_json(SC_CALL + ['connector__matrix__listen_audio', '--args', json.dumps({'audio_info': {'url': up['temp_url'], 'mime_type': 'audio/mpeg', 'prompt': prompt}})])
    return t.get('transcription', json.dumps(t, ensure_ascii=False))


# ================================================================ edge：edge-tts
EDGE_VOICE_EN = 'en-US-GuyNeural'   # edge 后端英文稿的默认音色
EDGE_VOICE = 'zh-CN-YunxiNeural'          # 自然的年轻男声；女声可用 zh-CN-XiaoxiaoNeural，播音腔男声 zh-CN-YunyangNeural


def edge_probe():
    if importlib.util.find_spec('edge_tts') is None:
        return False, '没有安装 edge-tts（安装：python3 -m pip install edge-tts，合成时需要联网）'
    return True, 'edge-tts 已安装'


def edge_stream(text, e):
    """一次合成：返回 (mp3 字节, [(t0, t1, 词)])。拿不到词级边界时第二项为空。"""
    import edge_tts
    audio = bytearray(); words = []

    async def go():
        kw = dict(rate=e.get('rate', '+0%'), volume=e.get('volume', '+0%'))
        try:
            c = edge_tts.Communicate(text, e.get('voice', EDGE_VOICE), boundary='WordBoundary', **kw)
        except TypeError:                     # 旧版本没有 boundary 参数，默认就给词级边界
            c = edge_tts.Communicate(text, e.get('voice', EDGE_VOICE), **kw)
        async for ch in c.stream():
            if ch['type'] == 'audio':
                audio.extend(ch['data'])
            elif ch['type'] == 'WordBoundary':
                words.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    for k in range(4):
        try:
            asyncio.run(go())
            if audio: return bytes(audio), words
        except Exception as ex:
            print(f'  edge-tts 重试 {k + 1}：{str(ex)[:140]}', flush=True)
        audio.clear(); words.clear(); time.sleep(5 * (k + 1))
    raise SystemExit('edge-tts 合成失败（需要联网）。可以换音色、稍后再试，或改用录音（voice.provider = "file"）。')


def norm(s):
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', s.lower())


def char_map(text_n, words):
    """配音稿的每个有效字 → 它所在的词序号（找不到的为 None）"""
    wn = ''; owner = []
    for i, (_, _, t) in enumerate(words):
        n = norm(t); wn += n; owner += [i] * len(n)
    m = [None] * len(text_n)
    for a, b, size in difflib.SequenceMatcher(None, text_n, wn, autojunk=False).get_matching_blocks():
        for j in range(size): m[a + j] = owner[b + j]
    return m


def edge_full(v, text, tag):
    import numpy as np
    e = dict(v.get('edge') or {})
    if not e.get('voice'):
        e['voice'] = EDGE_VOICE_EN if script_lang() == 'en' else EDGE_VOICE
        print(f'未指定音色，按配音稿语言用 edge 的 {e["voice"]}', flush=True)
    text = re.sub(TAGS, '', text)                                    # (breath) 这类标记 edge-tts 会照字读出来
    parts = re.split(MARK, text); chunks = parts[0::2]; pauses = [float(p) for p in parts[1::2]]
    tmp = Path(tempfile.mkdtemp(prefix='lucid_edge_'))
    print(f'  音色 {e.get("voice", EDGE_VOICE)}，语速 {e.get("rate", "+0%")}', flush=True)
    mp3b, words = edge_stream(''.join(chunks), e)
    (tmp / 'all.mp3').write_bytes(mp3b); x = decode(tmp / 'all.mp3')
    # 每个停顿标记前后的词：前一段最后一个字、后一段第一个字
    cuts = None
    if words:
        ns = [norm(c) for c in chunks]; m = char_map(''.join(ns), words); pos = 0; cuts = []
        for i in range(len(pauses)):
            pos += len(ns[i])
            a = next((m[j] for j in range(pos - 1, -1, -1) if m[j] is not None), None)
            b = next((m[j] for j in range(pos, len(m)) if m[j] is not None), None)
            if a is None or b is None or b <= a:
                cuts = None; break
            cuts.append((words[a][1], words[b][0]))
    out_words = []
    if cuts:                                                         # 整段合成：在停顿标记处切开，停顿补到标记的时长
        segs = []; prev = 0.0
        for (t_end, t_next), p in zip(cuts, pauses):
            mid = (t_end + t_next) / 2
            ca = min(t_end + 0.08, mid); cb = max(t_next - 0.03, mid)
            segs.append((prev, ca, p)); prev = cb
        segs.append((prev, len(x) / SR, 0.0))
        y = []; t_out = 0.0
        for a, b, p in segs:
            for w0, w1, wt in words:
                if a - 1e-3 <= w0 < b: out_words.append({'text': wt, 't0': round(w0 - a + t_out, 3), 't1': round(min(w1, b) - a + t_out, 3)})
            y.append(x[int(a * SR):int(b * SR)]); y.append(np.zeros(int(p * SR), np.float32)); t_out += (b - a) + p
        y = np.concatenate(y)
        print(f'  整段合成，{len(words)} 个词级边界，{len(pauses)} 处停顿标记已补足时长', flush=True)
    else:                                                            # 拿不到边界：按停顿标记分段合成再拼接
        print('  没拿到可用的词级边界，改为按停顿标记分段合成', flush=True)
        y = []; t_out = 0.0
        for i, c in enumerate(chunks):
            b, ws = edge_stream(c, e) if norm(c) else (b'', [])
            seg = np.zeros(0, np.float32)
            if b:
                (tmp / f'c{i}.mp3').write_bytes(b); seg = decode(tmp / f'c{i}.mp3')
            out_words += [{'text': wt, 't0': round(w0 + t_out, 3), 't1': round(w1 + t_out, 3)} for w0, w1, wt in ws]
            p = pauses[i] if i < len(pauses) else 0.0
            y += [seg, np.zeros(int(p * SR), np.float32)]; t_out += len(seg) / SR + p
        y = np.concatenate(y)
    wav = AUDIO / f'narration_{tag}.wav'; write_wav(y, wav)
    mp3 = to_mp3(wav, AUDIO / f'narration_{tag}.mp3')
    shutil.rmtree(tmp, ignore_errors=True)
    return mp3, wav, ({'duration': round(len(y) / SR, 3), 'words': out_words} if out_words else None)


# ================================================================ file：用户给的录音
def file_probe(v):
    f = (v.get('file') or {}).get('audio')
    if not f:
        return False, 'voice.file.audio 没有写录音文件'
    if not (ROOT / f).exists():
        return False, f'录音文件不存在：{f}'
    return True, f'录音 {f}'


def file_full(v, text, tag):
    src = ROOT / v['file']['audio']
    wav = AUDIO / f'narration_{tag}.wav'
    tmp = Path(tempfile.mkdtemp(prefix='lucid_file_')) / 'in.wav'
    to_wav(src, tmp); shutil.move(str(tmp), wav)                     # 先转到临时文件：录音本身可能就叫 narration.wav
    return to_mp3(wav, AUDIO / f'narration_{tag}.mp3'), wav, None


# ================================================================ 选后端
PROBES = {'mcode': lambda v: mcode_probe(), 'edge': lambda v: edge_probe(), 'file': file_probe}
FULL = {'mcode': mcode_full, 'edge': edge_full, 'file': file_full}
AUTO = ['mcode', 'edge']


def pick(v, quiet=False):
    want = v.get('provider', 'auto')
    if want not in ('auto', *FULL):
        raise SystemExit(f'voice.provider 只能是 auto、mcode、edge、file，现在是 {want!r}')
    if want != 'auto':
        ok, why = PROBES[want](v)
        if not ok: raise SystemExit(f'配音后端 {want} 不可用：{why}')
        if not quiet: print(f'配音后端：{want}（project.json 指定；{why}）')
        return want
    tried = []
    for name in AUTO:
        ok, why = PROBES[name](v)
        if ok:
            if not quiet: print(f'配音后端：{name}（auto；{why}' + ''.join(f'；{n} 不可用：{w}' for n, w in tried) + '）')
            return name
        tried.append((name, why))
    raise SystemExit('没有可用的配音后端：\n' + ''.join(f'  {n}：{w}\n' for n, w in tried) +
                     '可以：① 安装 edge-tts（python3 -m pip install edge-tts）后重跑；'
                     '② 请用户提供录好的配音，写 voice.provider = "file"、voice.file.audio；'
                     '③ 做无配音版本（timeline.mode 改为 beats 或 manual，用画面文字讲）。')


def cmd_probe():
    v = project().get('voice', {})
    for name in ('mcode', 'edge', 'file'):
        ok, why = PROBES[name](v)
        print(f"  {'✓' if ok else '✗'} {name:6s} {why}")
    try: pick(v)
    except SystemExit as e: print(e)


def cmd_full(tag):
    v = project().get('voice', {})
    name = pick(v)
    text, n = script_text(v)
    AUDIO.mkdir(exist_ok=True)
    print(f'{"导入录音" if name == "file" else "合成"}：{len(text)} 字，{n} 个镜头 …', flush=True)
    mp3, wav, words = FULL[name](v, text, tag)
    for src, dst in ((mp3, 'narration.mp3'), (wav, 'narration.wav')):
        (AUDIO / dst).write_bytes(Path(src).read_bytes())
    if words:
        json.dump(dict(words, audio='narration.wav', provider=name), open(WORDS, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    elif WORDS.exists():
        WORDS.unlink()                                               # 旧配音的词级时间，留着会对错位置
    voice = {'mcode': lambda: v.get('voice_id') or default_voice(), 'edge': lambda: (v.get('edge') or {}).get('voice') or (EDGE_VOICE_EN if script_lang() == 'en' else EDGE_VOICE),
             'file': lambda: '录音 ' + v['file']['audio']}[name]()
    json.dump({'provider': name, 'voice': voice, 'speed': v.get('speed') if name == 'mcode' else (v.get('edge') or {}).get('rate') if name == 'edge' else None,
               'why': v.get('why') if (name == 'mcode' and v.get('voice_id')) or (name == 'edge' and (v.get('edge') or {}).get('voice')) or name == 'file' else None,   # 理由只对工程指定的音色有效
               'tag': tag, 'time': time.strftime('%Y-%m-%d %H:%M')}, open(AUDIO / 'narration.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已保存', mp3, wav, '和词级时间 ' + str(WORDS) if words else '')


def cmd_once(args_file, out):
    v = project().get('voice', {}); name = pick(v)
    a = json.load(open(args_file, encoding='utf-8'))
    if name == 'mcode':
        return mcode_synth(args_file, out)
    if name == 'edge':
        e = dict(v.get('edge') or {}); e.update({k: a[k] for k in ('voice', 'rate', 'volume') if k in a})
        b, _ = edge_stream(re.sub(TAGS + '|' + MARK, '', a['text']), e); Path(out).write_bytes(b); return out
    raise SystemExit('录音后端不能试读：请用户重录这一句，或换成 mcode / edge 试读。')


_PROBE = {}


def asr_probe():
    if 'mcode' not in _PROBE: _PROBE['mcode'] = mcode_probe()
    return _PROBE['mcode']


_CN = '零一二三四五六七八九'


def cn_readings(tok):
    """数字的中文读法：数值读法（两千零二十四、三点五、百分之七十）和逐位读法（二零二四）"""
    pct = tok.endswith('%'); tok = tok.rstrip('%')
    def num(n):
        if n == 0: return '零'
        units = ['', '十', '百', '千']; big = ['', '万', '亿']; out = ''; k = 0
        while n > 0:
            g = n % 10000; n //= 10000
            if g:
                t = ''; z = False
                for i in range(3, -1, -1):
                    d = g // 10 ** i % 10
                    if d: t += ('零' if z and t else '') + _CN[d] + units[i]; z = False
                    elif t: z = True
                out = t + big[k] + ('零' if out and g < 1000 else '') + out
            elif out and not out.startswith('零'): out = '零' + out
            k += 1
        return re.sub(r'^一十', '十', out)
    i, _, f = tok.partition('.')
    try: n = int(i)
    except ValueError: return []
    r = [num(n) + ('点' + ''.join(_CN[int(c)] for c in f) if f else ''), ''.join(_CN[int(c)] for c in i) + ('点' + ''.join(_CN[int(c)] for c in f) if f else '')]
    r += [x.replace('二', '两', 1) for x in r if x.startswith('二') and len(x) > 1]
    return ['百分之' + x for x in r] if pct else r


def compare(script, heard):
    """稿子和转写对不上的地方：(英文词, 数字, 其他 [(稿, 转写, 前后文)])"""
    clean = lambda x: re.sub(MARK + '|' + TAGS, '', x)
    script = clean(script); nrm = lambda x: re.sub(r'[\s\-_.,，。；：？！、"“”「」‘’（）()《》…—·]', '', x).lower()
    H = nrm(heard)
    eng = sorted({w for w in re.findall(r'[A-Za-z][A-Za-z0-9.]+', script) if nrm(w) not in H})
    nums = sorted({w for w in re.findall(r'\d+(?:\.\d+)?%?', script) if nrm(w) not in H and not any(r in H for r in cn_readings(w))})
    S = nrm(script); other = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, S, H, autojunk=False).get_opcodes():
        if op == 'equal' or not re.search(r'[\u4e00-\u9fff]', S[a0:a1] + H[b0:b1]): continue
        if a1 - a0 > 8 or b1 - b0 > 8 or re.fullmatch(r'[的得地了啊呀吧呢嘛]*', S[a0:a1]) and re.fullmatch(r'[的得地了啊呀吧呢嘛]*', H[b0:b1]): continue
        if re.search(r'[0-9a-z]', S[a0:a1]): continue                     # 英文词和数字上面单独报
        other.append((S[a0:a1] or '（无）', H[b0:b1] or '（漏读）', S[max(0, a0 - 6):a1 + 6]))
    return eng, nums, other


def cmd_asr(tag, quiet_missing=False):
    ok, why = asr_probe()
    if not ok:
        print(f'无法自动核对读音：没有可用的转写后端（{why}）。\n'
              '  → 请用户试听 audio/narration.mp3，重点听英文名、多音字、数字；在交付说明里写明读音没有经过自动核对。')
        return
    import numpy as np, scipy.io.wavfile as w
    wav = AUDIO / ('narration.wav' if tag == 'current' else f'narration_{tag}.wav')
    sr, x = w.read(str(wav)); x = x.astype(np.float32) / 32768
    hop = int(.005 * sr); n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    gaps = []; s = None
    for i, vv in enumerate(db < -45):
        if vv and s is None: s = i
        if not vv and s is not None:
            if (i - s) * .005 >= 1.0: gaps.append((s + i) / 2 * .005)
            s = None
    cuts = [0.0]
    for g in gaps:
        if g - cuts[-1] >= 110: cuts.append(g)           # 约 2 分钟一段，在镜头间隙处切
    cuts.append(len(x) / sr)
    out_dir = AUDIO / 'asr'; out_dir.mkdir(exist_ok=True)
    texts = []
    for k in range(len(cuts) - 1):
        f = out_dir / f'{tag}_part{k}.mp3'
        subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-ss', str(cuts[k]), '-to', str(cuts[k + 1]), '-i', str(wav), '-b:a', '128k', str(f)], check=True)
        t = transcribe(f); (out_dir / f'{tag}_part{k}.txt').write_text(t, encoding='utf-8'); texts.append(t)
        print(f'  段 {k}  {cuts[k]:.0f}–{cuts[k + 1]:.0f}s 已转写', flush=True)
    VO, fix = vo(); script = ' '.join(t for _, t in VO)
    eng, nums, other = compare(script, ''.join(texts))
    other = [o for o in other if not any(o[0] in a or o[0] in b for a, b in fix.items())]     # tts_fix 换过的同音字不算
    print('\n读音核对（稿子 script/vo.json 对转写）：')
    print('  英文词可能读错（转写里找不到）：', eng or '没有')
    print('  数字可能读错（阿拉伯数字和中文读法都找不到）：', nums or '没有')
    if other:
        print(f'  其他对不上的词 {len(other)} 处（多是名字、多音字、同音字；转写本身也可能写错同音字，逐条判断）：')
        for a, b, ctx in other[:20]: print(f'    稿「{a}」→ 听成「{b}」　…{ctx}…')
        if len(other) > 20: print(f'    …还有 {len(other) - 20} 处')
    else: print('  其他词：都对得上')
    if eng or nums or other:
        print('  → 先用 tts once 短句试读几种写法；仍读不准就改成中文指代，或在 vo.json 的 tts_fix 里换同音字（画面文字不变），然后重新 full。')
    print('全文转写在', out_dir)


# ================================================================ 选音色：voices 列候选，audition 同一句话试读比较
# mcode 的在线音色列表拿不到时列这份常用音色（MiniMax 系统音色）；voice_id 以合成工具为准，用 audition 试读一次就知道能不能用
MM_COMMON = [
    ('Chinese (Mandarin)_Gentleman', 'zh', '男 · 中年', '温润男声，稳、亲切，科普和讲解的推荐音色'),
    ('Chinese (Mandarin)_Gentle_Youth', 'zh', '男 · 青年', '温润青年，轻快不油腻，适合年轻观众的知识片'),
    ('Chinese (Mandarin)_Reliable_Executive', 'zh', '男 · 中年', '沉稳高管，可信、干练，适合商业发布、产品讲解'),
    ('Chinese (Mandarin)_Male_Announcer', 'zh', '男 · 中年', '播报男声，字正腔圆，新闻和纪录片口吻'),
    ('Chinese (Mandarin)_Radio_Host', 'zh', '男 · 青年', '电台主播，松弛、有陪伴感'),
    ('Chinese (Mandarin)_Lyrical_Voice', 'zh', '男 · 青年', '抒情男声，柔和，适合故事和人文题材'),
    ('Chinese (Mandarin)_News_Anchor', 'zh', '女 · 中年', '新闻女主播，清晰、正式'),
    ('Chinese (Mandarin)_Wise_Women', 'zh', '女 · 中年', '阅历姐姐，从容、有分寸，适合讲道理、讲历史'),
    ('Chinese (Mandarin)_Sweet_Lady', 'zh', '女 · 青年', '甜美女声，亲和，适合生活方式、消费产品'),
    ('Chinese (Mandarin)_Warm_Girl', 'zh', '女 · 少女', '温暖少女，明亮、有朝气'),
    ('Chinese (Mandarin)_Kind-hearted_Antie', 'zh', '女 · 中老年', '热心大婶，接地气，适合生活科普'),
    ('Chinese (Mandarin)_Cute_Spirit', 'zh', '中性 · 卡通', '憨憨萌兽，卡通角色感，适合儿童片里的角色'),
    ('male-qn-qingse', 'zh', '男 · 青年', '青涩青年'),
    ('male-qn-jingying', 'zh', '男 · 青年', '精英青年，利落、自信'),
    ('male-qn-daxuesheng', 'zh', '男 · 青年', '大学生，自然、口语化'),
    ('female-shaonv', 'zh', '女 · 少女', '少女音'),
    ('female-yujie', 'zh', '女 · 青年', '御姐音，成熟、有气场'),
    ('female-chengshu', 'zh', '女 · 中年', '成熟女性，平稳'),
    ('female-tianmei', 'zh', '女 · 青年', '甜美女性'),
    ('presenter_male', 'zh', '男 · 中年', '男主持人，舞台感'),
    ('presenter_female', 'zh', '女 · 中年', '女主持人，舞台感'),
    ('audiobook_male_1', 'zh', '男 · 中年', '有声书男声，适合长篇讲述'),
    ('audiobook_female_1', 'zh', '女 · 中年', '有声书女声，适合长篇讲述'),
    ('clever_boy', 'zh', '男 · 儿童', '聪明男童，儿童片的讲述者或角色'),
    ('cute_boy', 'zh', '男 · 儿童', '可爱男童'),
    ('lovely_girl', 'zh', '女 · 儿童', '萌萌女童，儿童片的讲述者或角色'),
    ('English_expressive_narrator', 'en', 'male · adult', '富有表现力的英文旁白，纪录片和讲解'),
    ('English_Trustworth_Man', 'en', 'male · adult', '可信、沉稳的英文男声，产品和商业'),
    ('English_Gentle-voiced_man', 'en', 'male · adult', '温和的英文男声'),
    ('English_magnetic_voiced_man', 'en', 'male · adult', '有磁性的英文男声，发布片'),
    ('English_Graceful_Lady', 'en', 'female · adult', '优雅的英文女声'),
    ('English_CalmWoman', 'en', 'female · adult', '平静的英文女声，讲解'),
    ('English_Upbeat_Woman', 'en', 'female · young', '轻快的英文女声，消费产品'),
]
EDGE_ID = re.compile(r'^[a-z]{2,3}-[A-Z]{2}(?:-[a-z]+)?-\w+Neural$')
EDGE_ZH = {'Warm': '温暖', 'Lively': '活泼', 'Passion': '激昂', 'Sunshine': '阳光', 'Cute': '可爱', 'Professional': '专业', 'Reliable': '可靠',
           'Humorous': '幽默', 'Bright': '明亮', 'Cartoon': '卡通', 'News': '新闻', 'Novel': '小说', 'Sports': '体育', 'Dialect': '方言'}


def _flag(a, name, default=None):
    if name in a: i = a.index(name); val = a[i + 1]; del a[i:i + 2]; return val
    return default


def mm_lang(vid, text=''):
    """MiniMax 音色的语言：前缀（Chinese (Mandarin)_、English_ 等），没有前缀的看写法（小写拼音风格是中文，首字母大写的英文名是英文）"""
    m = re.match(r'([A-Za-z]+)(?:\s*\([^)]*\))?_', vid)
    known = {'Chinese': 'zh', 'Cantonese': 'zh', 'English': 'en', 'Japanese': 'ja', 'Korean': 'ko', 'Spanish': 'es', 'French': 'fr',
             'German': 'de', 'Portuguese': 'pt', 'Russian': 'ru', 'Italian': 'it', 'Arabic': 'ar', 'Indonesian': 'id', 'Vietnamese': 'vi', 'Thai': 'th'}
    if m and m.group(1) in known: return known[m.group(1)]
    if re.fullmatch(r'[a-z0-9_\-]+', vid): return 'zh'
    if re.search(r'[\u4e00-\u9fff]', text) and not re.fullmatch(r'[A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+', vid): return 'zh'
    return 'en' if re.fullmatch(r'[A-Z][A-Za-z0-9]*(?:[_\-][A-Za-z0-9]+)+', vid) else '?'


def _find_voice_dicts(x, out):
    if isinstance(x, dict):
        if isinstance(x.get('voice_id'), str): out.append(x)
        else:
            for y in x.values(): _find_voice_dicts(y, out)
    elif isinstance(x, list):
        for y in x: _find_voice_dicts(y, out)
    elif isinstance(x, str) and x.strip()[:1] in '[{':
        try: _find_voice_dicts(json.loads(x), out)
        except Exception: pass
    return out


def mcode_voice_list():
    """在线音色列表：[(voice_id, 语言, 性别年龄, 描述)]；拿不到返回 (None, 原因)"""
    ok, why = mcode_probe()
    if not ok: return None, why
    try:
        r = subprocess.run(['mcode-tools', 'connector', 'tools', '--keyword', 'voice'], capture_output=True, text=True, timeout=90)
        names = sorted(set(re.findall(r'connector__\w+?__\w*voice\w*', r.stdout)))
        name = next((n for n in names if 'list' in n), None) or next((n for n in names if 'get_voice' in n), None)
        if not name: return None, '没找到音色列表工具（mcode-tools connector tools --keyword voice 里没有 *voice_list*）'
        s = subprocess.run(['mcode-tools', 'connector', 'tool', name], capture_output=True, text=True, timeout=90).stdout
    except subprocess.TimeoutExpired:
        return None, 'mcode-tools 90 秒内没有响应'
    args = {'voice_type': 'all'} if '"voice_type"' in s else {}
    try: d = run_json(SC_CALL + [name, '--args', json.dumps(args)], tries=3)
    except SystemExit as e: return None, f'{name} 调用失败：{str(e)[:160]}'
    rows, seen = [], set()
    for x in _find_voice_dicts(d, []):
        vid = x['voice_id']
        if vid in seen: continue
        seen.add(vid)
        nm = x.get('voice_name') or x.get('name') or ''
        desc = x.get('description') or x.get('desc') or ''
        desc = '；'.join(map(str, desc)) if isinstance(desc, list) else str(desc)
        ga = ' · '.join(str(x[k]) for k in ('gender', 'age') if x.get(k)) or '—'
        rows.append((vid, mm_lang(vid, nm + desc), ga, '，'.join(s_ for s_ in (nm, desc) if s_) or '—'))
    return (rows, f'在线音色列表（{name}）') if rows else (None, f'{name} 没有返回音色')


def edge_voice_list():
    import edge_tts
    try: vs = asyncio.run(asyncio.wait_for(edge_tts.list_voices(), 30))
    except Exception as ex: return None, f'edge-tts 音色表拿不到（需要联网）：{str(ex)[:120]}'
    rows = []
    for x in vs:
        loc = x.get('Locale', ''); lang = loc.split('-')[0]
        tag = x.get('VoiceTag') or {}
        tr = (lambda w: EDGE_ZH.get(w.strip(), w.strip())) if lang == 'zh' else (lambda w: w.strip())   # 中文音色的描述译成中文，其余保留原词（--grep 按原词搜）
        pers = [tr(p) for p in tag.get('VoicePersonalities') or []]
        cats = [tr(c) for c in tag.get('ContentCategories') or []]
        g = {'Male': '男', 'Female': '女'}.get(x.get('Gender'), x.get('Gender', '—'))
        rows.append((x['ShortName'], lang, f'{g} · {loc}', '、'.join(pers) + (f'；适合 {"、".join(cats)}' if cats else '')))
    return rows, 'edge-tts 音色表'


def cmd_voices(a):
    lang, kw, prov = _flag(a, '--lang'), _flag(a, '--grep'), _flag(a, '--provider')
    v = project().get('voice', {})
    prov = prov or ('mcode' if v.get('provider', 'auto') == 'file' else pick(v, quiet=True))
    if prov not in ('mcode', 'edge'): raise SystemExit('--provider 只能是 mcode 或 edge')
    if prov == 'edge':
        if not edge_probe()[0]: raise SystemExit(edge_probe()[1])
        rows, src = edge_voice_list()
        if rows is None: raise SystemExit(src)
    else:
        rows, src = mcode_voice_list()
        if rows is None:
            print(f'在线音色列表拿不到（{src}），下面是常用音色：voice_id 以合成工具为准，用 audition 试读一次确认能用')
            rows, src = MM_COMMON, '常用音色（内置）'
    if lang: rows = [r for r in rows if r[1] == lang or r[1] == '?']
    if kw: rows = [r for r in rows if kw.lower() in ' '.join(r).lower()]
    print(f'{src}：{len(rows)} 个' + (f'（--lang {lang}）' if lang else '') + (f'（--grep {kw}）' if kw else ''))
    wid = max([len(r[0]) for r in rows] + [10])
    for vid, lg, ga, desc in rows:
        print(f'  {vid:<{wid}}  {ga:<14}  {desc}' + ('　（推荐）' if vid == RECOMMENDED else ''))
    print('挑 2–3 个合适的：python3 tools/tts.py audition "<片子里的一句话>" <voice_id> <voice_id> …')


def cmd_audition(a):
    speed = float(_flag(a, '--speed', project().get('voice', {}).get('speed', 1.12)))
    if len(a) < 2: raise SystemExit('用法：python3 tools/tts.py audition "<一句话>" <voice_id> [<voice_id> ...] [--speed 1.1]')
    text, ids = a[0], a[1:]
    out_dir = AUDIO / 'audition'; out_dir.mkdir(parents=True, exist_ok=True)
    ok_asr, why_asr = asr_probe()
    n_chars = len(norm(re.sub(TAGS + '|' + MARK, '', text)))
    res = []
    for vid in ids:
        prov = 'edge' if EDGE_ID.match(vid) else 'mcode'
        ok, why = (edge_probe() if prov == 'edge' else asr_probe())
        if not ok:
            print(f'  ✗ {vid}：{prov} 不可用（{why}）'); continue
        safe = re.sub(r'[^\w\-]+', '_', vid).strip('_')
        mp3 = out_dir / f'{safe}.mp3'
        print(f'  合成 {vid}（{prov}）…', flush=True)
        try:
            if prov == 'edge':
                b, _ = edge_stream(re.sub(TAGS + '|' + MARK, '', text), {'voice': vid, 'rate': f'{round((speed - 1) * 100):+d}%'}); mp3.write_bytes(b)
            else:
                af = out_dir / f'{safe}.args.json'
                json.dump({'text': text, 'voice_id': vid, 'speed': speed, 'output_file': f'audition_{safe}'}, open(af, 'w', encoding='utf-8'), ensure_ascii=False)
                mcode_synth(af, mp3)
        except SystemExit as e:
            print(f'  ✗ {vid}：合成失败（{str(e)[:160]}）'); continue
        dur = len(decode(mp3)) / SR
        heard = transcribe(mp3) if ok_asr else None
        res.append((vid, dur, heard))
        if heard: (out_dir / f'{safe}.txt').write_text(heard, encoding='utf-8')
        print(f'  ✓ {vid}　{dur:.2f} 秒　{n_chars / max(dur, 1e-3):.1f} 字/秒　{mp3.relative_to(ROOT)}' + (f'\n      转写：{heard}' if heard else ''), flush=True)
    if not ok_asr: print(f'无法自动转写（{why_asr}）：只能比时长和语速，音色和语气请用户试听 audio/audition/ 里的文件')
    if res: print('选定后写进 project.json：voice.voice_id（edge 音色写 voice.edge.voice）和 voice.why（一句话：为什么选这个声音）')


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0] == 'probe': cmd_probe()
    elif a[0] == 'voices': cmd_voices(a[1:])
    elif a[0] == 'audition': cmd_audition(a[1:])
    elif a[0] == 'full':
        rest = [x for x in a[1:] if x != '--no-asr']; tag = rest[0] if rest else 'v1'
        cmd_full(tag)
        if '--no-asr' in a: print('按 --no-asr 跳过读音核对；需要时运行 python3 tools/tts.py asr current')
        else: print('\n合成完成，自动核对读音 …', flush=True); cmd_asr(tag)
    elif a[0] == 'asr': cmd_asr(a[1] if len(a) > 1 else 'current')
    elif a[0] == 'once':
        mp3 = cmd_once(a[1], a[2]); print('saved', mp3)
        if '--asr' in a:
            ok, why = asr_probe()
            print(transcribe(mp3) if ok else f'无法自动核对读音：{why}')
    else: print(__doc__)
