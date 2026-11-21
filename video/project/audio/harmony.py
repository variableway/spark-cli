"""调性与和弦：key 写 "A minor" / "F" / "D major" / "B♭"；和弦名写 Am F C G Em7 Dsus4 Cmaj7 Bm7 G7 Fadd9 ...
electronic / ambient 用 chord()；piano 只用 parse_key 取主音（织体沿用 v1 的 I–vi–IV–V）。"""
import re

PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
QUAL = {'': [0, 4, 7], 'm': [0, 3, 7], 'dim': [0, 3, 6], 'aug': [0, 4, 8], 'sus2': [0, 2, 7], 'sus4': [0, 5, 7], '5': [0, 7],
        '7': [0, 4, 7, 10], 'maj7': [0, 4, 7, 11], 'm7': [0, 3, 7, 10], 'add9': [0, 4, 7, 14], 'madd9': [0, 3, 7, 14],
        '9': [0, 4, 7, 10, 14], 'maj9': [0, 4, 7, 11, 14], 'm9': [0, 3, 7, 10, 14], '7sus4': [0, 5, 7, 10]}
ALIAS = {'min': 'm', 'maj': '', 'M': '', 'M7': 'maj7', 'min7': 'm7', 'mi7': 'm7', 'min9': 'm9', 'sus': 'sus4', '-': 'm', 'dom7': '7'}


def _pc(s):
    s = s.replace('♯', '#').replace('♭', 'b'); v = PC[s[0].upper()]
    for c in s[1:]: v += 1 if c == '#' else -1
    return v % 12


def parse_key(s):
    """'A minor' / 'Am' / 'F' / 'D major' / 'B♭' → (主音 pitch class, 是否小调)"""
    m = re.fullmatch(r'\s*([A-Ga-g][#♯b♭]?)\s*(major|minor|maj|min|m|M)?\s*', s or 'A minor')
    if not m: raise SystemExit(f'music.key 看不懂：{s!r}。写法示例："A minor"、"F"、"D major"、"B♭"')
    return _pc(m[1]), (m[2] or '') in ('minor', 'min', 'm')


def chord(name):
    """和弦名 → {name, pc, bass 低音根音 MIDI(36–47), notes 紧凑排列的和弦音(约 54–75), iv 音程}"""
    m = re.fullmatch(r'\s*([A-G][#♯b♭]?)(.*?)\s*', name)
    q = ALIAS.get(m[2], m[2]) if m else None
    if not m or q not in QUAL: raise SystemExit(f'和弦看不懂：{name!r}。可用后缀：{" ".join(repr(k) for k in QUAL)}（别名 {" ".join(ALIAS)}）')
    pc = _pc(m[1]); r4 = 60 + pc - (12 if pc >= 6 else 0)
    return {'name': name, 'pc': pc, 'bass': 36 + pc, 'notes': [r4 + i for i in QUAL[q]], 'iv': QUAL[q]}


def five(ch):
    """音效用：(低音根音, 五个和弦音) —— 和 v1 piano 的 triad9 同形，让 swell / chord_hit 等音效在任何 style 下都能用"""
    iv = list(ch['iv'])
    while len(iv) < 5: iv.append(iv[len(iv) - 3] + 12 if len(iv) > 2 else iv[-1] + 12)
    r = ch['bass'] + 12
    return ch['bass'], [r + i for i in iv[:5]]


def default_progression(tonic, minor):
    deg = [(0, 'm'), (8, ''), (3, ''), (10, '')] if minor else [(0, ''), (7, ''), (9, 'm'), (5, '')]   # i–VI–III–VII / I–V–vi–IV
    return [NAMES[(tonic + d) % 12] + q for d, q in deg]


def scale_notes(tonic, minor):
    pent = [0, 3, 5, 7, 10] if minor else [0, 2, 4, 7, 9]
    return [60 + tonic + p + 12 * o for o in range(-1, 3) for p in pent]
