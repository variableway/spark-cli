"""音节与短句：没有配音时按音节估时；有配音时，短句对齐按各短句的音节数分配发音时长。
中文每字 1 个音节；英文单词查 EN 表，查不到的按字母数 / 3 估算；project.json 的 en_syllables 可补充。"""
import re
from common import project

EN = {'Personal': 3, 'Agent': 2, 'OpenAI': 5, 'Meta': 2, 'AI': 2, 'App': 1, 'Code': 1, 'MiniMax': 3, 'Mac': 1, 'Studio': 3}
SPS = 0.229  # 估时用的语速：中速男声每音节约 0.229 秒（含标点自然停顿），voice.speed 会按比例换算
TAGS = r'\((?:breath|chuckle|laughs|sighs)\)'


def _en():
    d = dict(EN)
    d.update(project().get('en_syllables', {}))
    return d


def syl(text):
    en = _en()
    s = re.sub(TAGS + r'|<#[\d.]+#>', '', text)
    n = 0
    for w in sorted(en, key=len, reverse=True):
        n += len(re.findall(r'(?<![A-Za-z])' + re.escape(w) + r'(?![A-Za-z])', s)) * en[w]
        s = re.sub(r'(?<![A-Za-z])' + re.escape(w) + r'(?![A-Za-z])', ' ', s)
    for w in re.findall(r'[A-Za-z]+', s):
        n += max(1, round(len(w) / 3))
    n += len(re.findall(r'\d', s))
    return n + len(re.findall(r'[\u4e00-\u9fff]', s))


def pauses(text):
    return sum(float(x) for x in re.findall(r'<#([\d.]+)#>', text))


def phrases(text):
    """按标点切成短句（画面动作按短句序号对齐配音）"""
    t = re.sub(TAGS, '', text)
    parts = re.split(r'(<#[\d.]+#>|[，。；：？！、]|……)', t)
    out, cur = [], ''
    for p in parts:
        if not p:
            continue
        if re.fullmatch(r'<#[\d.]+#>|[，。；：？！、]|……', p):
            if cur.strip():
                out.append(cur.strip())
            cur = ''
        else:
            cur += p
    if cur.strip():
        out.append(cur.strip())
    return [p for p in out if syl(p) > 0]
