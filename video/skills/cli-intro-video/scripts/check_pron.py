#!/usr/bin/env python3
"""读音自检：配音稿里的多音字，TTS 到底读成了什么。

为什么要有这个：片子里出现「一行命令」这种词，正确读音是 háng（行列的列），
但 TTS 常常读成 xíng（像「还行」的那个行）。**画面上写着「一行命令」，声音说「一兴」，
观众一听就发现不对**——这类错误不报错、不告警，肉眼听一遍才发现。

而且 ASR 查不出来：转写只会把字还原成「行」，háng 和 xíng 都写成「行」，
拿转写比对读音等于没比（实测：`tts.py` 的读音核对对「行」完全无感）。

所以这个脚本做两件事：
  1. 静态：扫出配音稿里所有多音字，每一处配一个**期望读音**。期望值写在
     profile 的 pronunciation.rules 里——是数据不是代码，人来维护。
  2. 动态（--ask）：按镜头切出那段音频，用 mcode-tools 的音频问答逐处问
     「这个词实际读什么音」，和期望值比。**比的是音节**（háng vs xíng 音节不同，
     会被拦下；棵 vs 颗 音节相同，不会误报）。

模型不可靠的情况要显式标注：音频问答模型对「命令行」这类词会按「命令+行」的语义
拆字，答成 mìng lìng háng（标准读法是 mìng lìng）。这类词在规则表里标
`model_unreliable: true`，静态照常列出，但 `--ask` 不参与判定。

用法：
  python3 scripts/check_pron.py --project video/project --profile video/profile
  python3 scripts/check_pron.py ... --ask          # 调 mcode-tools 逐段核对实际读音
  python3 scripts/check_pron.py ... --only S03,S04
  python3 scripts/check_pron.py ... --json

退出码：0 全部相符（或没有待确认项）；1 有读音不符或未覆盖的多音字；2 缺音频等没法核。
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (  # noqa: E402
    find_project, load_json, resolve_profile,
)

OK, BAD, SKIP = '✅', '❌', '⚠️'

# 常见多音字（技术类文案里读错的多）。只是「可能读错」，期望读音由 profile 给。
POLYPHONES = {
    '行': 'háng/xíng', '重': 'chóng/zhòng', '还': 'huán/hái', '分': 'fēn/fèn',
    '尽': 'jǐn/jìn', '长': 'cháng/zhǎng', '只': 'zhī/zhǐ', '种': 'zhǒng/zhòng',
    '相': 'xiāng/xiàng', '应': 'yīng/yìng', '着': 'zhe/zháo', '差': 'chā/chà',
    '藏': 'cáng/zàng', '传': 'chuán/zhuàn', '参': 'cān/shēn', '调': 'tiáo/diào',
    '载': 'zài/zǎi', '校': 'jiào/xiào', '强': 'qiáng/qiǎng', '曲': 'qū/qǔ',
    '薄': 'báo/bó', '削': 'xuē/xiāo', '难': 'nán/nàn', '率': 'lü/shuài',
    '卡': 'kǎ/qiǎ', '当': 'dāng/dàng', '好': 'hǎo/hào', '数': 'shù/shǔ',
    '少': 'shǎo/shào', '会': 'huì/kuài', '干': 'gān/gàn', '假': 'jiǎ/jià',
    '空': 'kōng/kòng', '乐': 'lè/yuè', '累': 'lèi/léi', '量': 'liàng/liáng',
    '宁': 'níng/nìng', '切': 'qiē/qiè', '散': 'sàn/sǎn', '似': 'sì/shì',
    '宿': 'sù/xiǔ', '鲜': 'xiān/xiǎn', '兴': 'xīng/xìng', '要': 'yào/yāo',
    '落': 'luò/là', '发': 'fā/fà', '冲': 'chōng/chòng', '模': 'mó/mú',
}

# 拼音音节表：判断一段回答里的词是不是拼音（避免把英文单词当读音）。
PINYIN = set("""
a ai an ang ao ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo
bu ca cai can cang cao ce cen ceng cha chai chan chang chao che chen cheng
chi chong chou chu chua chuai chuan chuang chui chun chuo ci cong cou cu cuan
cui cun cuo da dai dan dang dao de dei den deng di dia dian diao die ding
dong dou du duan dui dun duo e ei en eng er fa fan fang fei fen feng fo fou
fu ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui
gun guo ha hai han hang hao he hei hen heng hong hou hu hua huai huan huang
hui hun huo ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun ka
kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang kui kun kuo
la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu lo
long lou lu luan lun luo ma mai man mang mao me mei men meng mi mian miao
min ming mo mou mu na nai nan nang nao ne nei nen neng ni nian niang niao
nie nin ning niu nong nu nv nuan nuo o ou pa pai pan pang pao pei pen peng
pi pian piao pin ping po pou pu qi qia qian qiang qiao qie qin qing qiong
qu quan que qun ran rang rao re ren reng ri rong rou ru ruan rui run ruo sa
sai san sang sao se sen seng sha shai shan shang shao she shei shen sheng shi
shou shu shua shuai shuan shuang shui shun shuo si song sou su suan sui sun suo
ta tai tan tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun tuo
wa wai wan wang wei wen weng wo wu xi xia xian xiang xiao xie xin xing xiong
xiu xu xuan xue yai yan yang yao ye yi yin ying yo yong you yu yuan yue yun za
zai zan zang zao ze zei zen zeng zha zhai zhan zhang zhao zhe zhei zhen zheng
zhi zhong zhou zhu zhua zhuai zhuan zhuang zhui zhun zhuo zi zong zou zu zuan
zui zun zuo
""".split())

TONE_MAP = {
    'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
    'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
    'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
    'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
    'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
    'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v', 'ü': 'v',
}


def base_pinyin(s):
    """去掉声调与空格，只留音节（háng → hang；"chóng fù" → "chongfu）。"""
    s = (s or '').strip().lower()
    return ''.join(TONE_MAP.get(c, c) for c in s if not c.isspace())


def is_pinyin(s):
    """一串拼音（可能多音节）是否成立。"""
    parts = [p for p in (s or '').split() if p]
    return bool(parts) and all(base_pinyin(p) in PINYIN for p in parts)


# ---------------------------------------------------------------- 静态：找出多音字

def rules_of(profile):
    """期望读音表：profile.pronunciation.rules。每条 {word, char, pinyin, note?, model_unreliable?}。"""
    return (profile.get('pronunciation') or {}).get('rules') or []


def occurrences(vo, rules):
    """扫描配音稿，返回 [{scene, word, char, expect, note, model_unreliable, text}]。"""
    out = []
    for sc in vo.get('scenes', []):
        text = sc.get('text', '')
        for r in rules:
            word = r.get('word', '')
            if not word or word not in text:
                continue
            out.append({
                'scene': sc.get('id'), 'word': word, 'char': r.get('char', word[0]),
                'expect': r.get('pinyin', ''), 'note': r.get('note', ''),
                'model_unreliable': bool(r.get('model_unreliable')),
                'text': text,
            })
    # 规则没覆盖到的多音字：标成未知（需要补规则，或用 --ask 让 AI 去问）
    covered = {o['word'] for o in out}
    for sc in vo.get('scenes', []):
        text = sc.get('text', '')
        for ch in set(text):
            if ch in POLYPHONES and not any(ch in w and w in text for w in covered):
                out.append({'scene': sc.get('id'), 'word': ch, 'char': ch,
                            'expect': '', 'note': f'规则表未覆盖，可能读成 {POLYPHONES[ch]}',
                            'model_unreliable': False, 'text': text})
    return out


# ---------------------------------------------------------------- 动态：问实际读音

def mcode_ready():
    if not shutil.which('mcode-tools'):
        return False, 'PATH 上没有 mcode-tools（不在 MiniMax Code 里运行）'
    return True, 'mcode-tools 可用'


def run_json(cmd, tries=8):
    o = ''
    for _ in range(tries):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            o = 'timeout'
            continue
        o = r.stdout + r.stderr
        if 'MCODE_AUTH_PROVIDER' in o or 'unauthorized' in o.lower():
            raise SystemExit('mcode-tools 没有登录，不要重试：' + o.strip()[:200])
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except Exception:
                pass
    raise SystemExit('mcode-tools 调用失败：' + o[:300])


def upload(path):
    d = run_json(['mcode-tools', 'upload_temp_url', str(path)])
    return d.get('temp_url')


def ask_reading(url, words):
    """问一段音频里每个词的实际读音。返回 {word: pinyin} 和错误说明。"""
    prompt = (
        '这段中文音频里含有以下词语：' + '、'.join(words) + '。'
        '请只输出 JSON，格式为 {"readings":[{"word":"词","pinyin":"拼音"}]}，'
        '其中 pinyin 是该词在音频里的实际读音（带声调，例：háng）。'
        '不要输出别的内容。'
    )
    args = {'audio_info': [{'url': url, 'mime_type': 'audio/wav', 'prompt': prompt}]}
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(args, f, ensure_ascii=False)
        argf = f.name
    d = run_json(['mcode-tools', 'connector', 'call',
                  'connector__matrix__audios_understand', '--args-file', argf])
    res = (d.get('results') or [{}])[0]
    if not res.get('success'):
        return {}, res.get('error', '音频问答失败')
    txt = res.get('description', '')
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        return {}, '回答里没有 JSON：' + txt[:120]
    try:
        data = json.loads(m.group(0))
    except Exception:
        return {}, '回答里的 JSON 解析失败：' + txt[:120]
    out = {}
    for r in data.get('readings', []):
        w, p = r.get('word', ''), r.get('pinyin', '')
        if w and p and is_pinyin(p):
            out[w] = p
    return out, ''


def segment_for(scene_id, words, timeline, audio):
    """按词定位到时间轴里那一段（含首尾两个词所在的短句），切出音频片段。"""
    sc = (timeline.get('scenes') or {}).get(scene_id)
    if not sc:
        return None, ''
    hits = []
    for ph in sc.get('phrases') or []:
        txt = ph.get('text') or ''
        if any(w in txt for w in words):
            hits.append((float(ph.get('t0', 0)), float(ph.get('t1', 0))))
    if hits:
        t0 = max(0.0, min(t[0] for t in hits) - 0.4)
        t1 = max(t[1] for t in hits) + 0.6
    else:
        t0, t1 = float(sc.get('t0', 0)), float(sc.get('t1', 0))
    out = Path(tempfile.mkdtemp(prefix='pron_')) / f'{scene_id}.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0),
                    '-i', str(audio), str(out)], check=True)
    return out, f'{t0:.1f}–{t1:.1f}s'


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default=None, help='视频工程目录')
    ap.add_argument('--profile', default=None, help='profile 文件或目录')
    ap.add_argument('--ask', action='store_true', help='调 mcode-tools 核对实际读音')
    ap.add_argument('--only', default=None, help='只查这些镜头，逗号分隔')
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    a = ap.parse_args()

    project = find_project(a.project)
    profile_file = resolve_profile(a.profile, project)
    profile = load_json(profile_file)
    vo = load_json(project / 'script' / 'vo.json')
    rules = rules_of(profile)

    occ = occurrences(vo, rules)
    if a.only:
        keep = {s.strip() for s in a.only.split(',')}
        occ = [o for o in occ if o['scene'] in keep]

    timeline = {}
    tl_file = project / 'timeline.json'
    if tl_file.is_file():
        timeline = load_json(tl_file)
    audio = project / 'audio' / 'narration.wav'
    if not audio.is_file():
        audio = project / 'audio' / 'narration.mp3'

    results = []
    for o in occ:
        r = dict(o)
        r['actual'] = ''
        if not o['expect']:
            r['status'] = SKIP
            r['note'] = o['note'] or '期望读音未知'
        elif o['model_unreliable']:
            r['status'] = SKIP
            r['note'] = (o['note'] or '') + '；AI 对这个词的读音判断不可靠，不参与核对'
        else:
            r['status'] = OK
        results.append(r)

    if a.ask and audio.is_file():
        # 一个镜头只问一次：把该镜头里所有多音字一起交给音频问答
        by_scene = {}
        for r in results:
            if r['expect'] and not r['model_unreliable']:
                by_scene.setdefault(r['scene'], []).append(r)
        for scene_id, items in by_scene.items():
            words = [r['word'] for r in items]
            try:
                seg, span = segment_for(scene_id, words, timeline, audio)
                if seg is None:
                    for r in items:
                        r['status'] = SKIP
                        r['note'] = '时间轴里没有这一段'
                    continue
                actual, err = ask_reading(upload(seg), words)
                for r in items:
                    got = actual.get(r['word'], '')
                    if not got:
                        for w, p in actual.items():
                            if r['word'] in w or w in r['word']:
                                got = p
                                break
                    r['actual'] = got
                    r['note'] = f'片段 {span}'
                    if err:
                        r['status'] = SKIP
                        r['note'] = f'{span}；{err}'
                    elif not got:
                        r['status'] = SKIP
                        r['note'] = f'{span}；回答里没有这一处读音'
                    elif base_pinyin(got) == base_pinyin(r['expect']):
                        r['status'] = OK
                    else:
                        r['status'] = BAD
                        r['note'] = (f'{span}；期望 {r["expect"]}，实际 {got}。'
                                     f'换成没有歧义的同义说法（如「一行」→「一条」），'
                                     f'或在 profile 的 pronunciation.rules 里标 model_unreliable')
            except Exception as e:  # noqa: BLE001
                for r in items:
                    r['status'] = SKIP
                    r['note'] = f'调用失败：{e}'

    bad = [r for r in results if r['status'] == BAD]
    unknown = [r for r in results if not r['expect']]
    skipped = [r for r in results if r['status'] == SKIP]

    if a.json:
        print(json.dumps({'results': results, 'bad': len(bad),
                          'unknown': len(unknown), 'skipped': len(skipped)},
                         ensure_ascii=False, indent=2))
    else:
        print(f'读音自检：{profile.get("name")}（工程 {project}）')
        if not results:
            print('  稿子里没有多音字。')
        for r in results:
            tail = f' → 实际 {r["actual"]}' if r['actual'] else ''
            print(f'  {r["status"]} {r["scene"]:<4} {r["word"]:<8} 期望 {r["expect"] or "?"}{tail}')
            if r.get('note'):
                print(f'      {r["note"]}')
        print(f'\n相符 {len(results) - len(bad) - len(unknown) - len(skipped)} · '
              f'不符 {len(bad)} · 未覆盖 {len(unknown)} · 核不了 {len(skipped)}')
        if unknown:
            print('  未覆盖的多音字：给它们在 profile.pronunciation.rules 里补一条期望读音，'
                  '或加 --ask 让 AI 去问。')
        if a.ask and not audio.is_file():
            print('  （没有 audio/narration.wav 或 .mp3，--ask 跳过了实际读音核对）')

    if bad:
        print('\n有读音不符：先改配音稿（vo.json）与画面文案，再重录配音，别带着它渲染。')
        sys.exit(1)
    if unknown and a.only is None:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
