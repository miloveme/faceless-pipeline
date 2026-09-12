"""채널 공정 공통 모듈. 모든 단계 스크립트가 이 파일만 import한다.
경로 규약: <EP>/script, <EP>/audio, <EP>/edit, <EP>/source  (EP = Channel/E06_popfilter 같은 에피소드 폴더)
"""
import hashlib, json, os, re, subprocess, sys, time, pathlib, urllib.request, difflib

CHANNEL = pathlib.Path(__file__).resolve().parent.parent          # 저장소 루트
PIPE_DIR = pathlib.Path(__file__).resolve().parent                # <repo>/pipeline — 읽기 사전·whisper 교정표
VOICE_DIR = PIPE_DIR                                              # voice.json 과 참조 음성도 pipeline/ 안
# Remotion 위치는 환경변수가 우선, 없으면 저장소의 remotion/ (60/65_render_*.sh, check_setup.py 와 같은 곳)
REMOTION_DIR = pathlib.Path(os.environ.get("REMOTION_DIR") or (CHANNEL / "remotion")).expanduser()
# 에피소드 위치도 같은 규칙. 00_new_episode.sh 가 만드는 곳과 같아야 한다(거기도 EPISODES_DIR, 없으면 <repo>/episodes)
EPISODES_DIR = pathlib.Path(os.environ.get("EPISODES_DIR") or (CHANNEL / "episodes")).expanduser()

# 타이밍·음량 상수 (E06에서 확정)
LEAD = 0.5        # 씬 시작 후 내레이션 시작까지
GAP = 0.8         # 내레이션 끝 후 씬 끝까지
PAD = 0.35        # 마지막 단어 끝 + PAD 에서 트림
FADE = 0.08       # 트림 직전 페이드아웃
NAR_LUFS = -16    # 씬 단위 내레이션. **모노 파일 기준**이다 — 40 이 -ac 1 로 만든다.
                  # 스테레오 마스터에서는 채널 복제로 **-13 으로 잡힌다**(+3.01).
                  # 클립 소재는 원래 스테레오라 그대로다 — **두 값을 빼기 전에 채널 수를 본다.**
                  # 왜 그런지는 docs/RECORDING.md 「채널 수가 바뀌면 3.01 dB」(음악 감독)
NAR_LUFS_TOL = 1.5   # 씬 음량 허용 편차. "이 정도면 균일하다"의 선이지 "여기서 멈춰야 한다"의 선이 아니다
                     # (실제로 균일성이 깨지는 것은 3 LU 부터). 그래서 종료코드를 걸지 않는다
NAR_TP_MAX = 0       # 위험한 것은 클리핑이고 그 선은 0 dBFS 다. 전 씬이 -1.5 에 붙는 것은
                     # TP 한계가 게인을 막은 구조적 결과라 거기에 문턱을 두면 반올림 한 자리에 멈춘다.
                     # 판정은 아래 clipped() — 풀스케일 이상 샘플 수 0 (참조 음성 합격선과 같은 기준)
MASTER_LUFS = -14 # 최종 마스터
MASTER_TP = -1.5     # 마스터 loudnorm 의 트루피크 천장. 60 의 `loudnorm=…:TP=…` 가 이 값을 쓴다.
                     # **판정선이 아니라 목표선이다.** ebur128 의 Peak 은 dBFS 한 자리로 반올림돼
                     # 실측이 -1.5 와 -1.4 로 갈린다(E01 마스터 일곱 장: -1.5 다섯 · -1.4 둘).
                     # 여기에 문턱을 두면 멀쩡한 마스터 둘이 걸린다 — NAR_TP_MAX 와 같은 이유다.
                     # 마스터도 판정은 clipped() 로 한다.
MASTER_LUFS_TOL = 0.5   # 마스터 음량 허용 편차(음악 감독). 두 패스 linear 가 TP 한계에 걸리면
                        # 게인을 스스로 낮춰 목표에 못 닿는데, 조용히 -15.2 로 나가면 유튜브
                        # 정규화가 다시 올리면서 맞춰 놓은 구간 관계가 흔들린다.
MASTER_LRA = 11      # 마스터 loudnorm 의 LRA. 60 의 `loudnorm=…:LRA=…` 가 이 값을 쓴다.
BGM_LUFS = -27    # 배경음악
CER_MAX = 0.06    # 씬 단위 글자 오류율 상한(전처리 후 기준, 30단계가 판정에 쓴다)
# 대본 길이 가늠 — 같은 숫자가 문서 둘·코드 하나·역할 정의 하나에 흩어져 8.4·8.5·25 가 동시에 있었다. 여기 하나로 둔다.
# **세는 방법이 값의 일부다.** 공백을 포함한 대본 원문 자수 ÷ 내레이션 실측 초, 강조 표시(**…**)는 뺀다.
# 05 의 spoken() 이 같은 방식으로 센다. 공백을 빼면 같은 대본이 6.78 이라 방법이 갈리면 3할이 어긋난다.
# 잰 표본 — 전부 voice.json 의 지금 목소리다:
#   E01 v5  24씬  3,195자 / 366.1초 = 8.73
#   E01 v8  29씬  **8.9 안팎**   ← 한 씬을 다시 만들 때마다 소수 둘째가 움직인다(8.88 → 8.90 …).
#                                 박아 두면 다음 편에서 어긋나고, 그때 누군가 값을 고친다(음악 감독)
# 중간 판본의 값은 안 적는다 — 그 판본이 없어져 **재현이 안 된다.** 남기면 다음 사람이 맞춰 보려다 못 한다.
# 표본 둘 다 8.7 보다 크다. **8.7 은 하한에 가까워 가늠이 늘 실측보다 넉넉하다** — 그게 이 값의 쓸모다.
# 그래서 **8.7 을 안 옮긴다**(음악 감독 판단). 옮기면 지난 편들의 가늠이 갈리는데,
# 얻는 정확도는 100자에 0.2초다. 정상 폭 밖으로 나가면 대본이 아니라 **음성이 흔들린 것**이다
# (SCRIPT_FORMAT.md 의 s07 사례 5.96자/초).
# 제공자·참조 음성·파라미터를 바꾸면 다시 재야 한다.
CHARS_PER_SEC = 8.7    # 대본 원문 기준(강조 표시 제외). 길이를 **가늠**하는 값이지 상한이 아니다
FPS = 30               # remotion/src/knowhow/Episode.tsx 의 FPS 와 같아야 한다 — 55 가 대조한다
WHISPER_MODEL = "medium"

if str(PIPE_DIR) not in sys.path: sys.path.insert(0, str(PIPE_DIR))

def die(msg, code=1):
    print("ERROR:", msg, file=sys.stderr); sys.exit(code)

def ep_dir(arg) -> pathlib.Path:
    """에피소드 폴더 찾기. 이름만 줘도(E01_x) 되고 경로로 줘도(episodes/E01_x, /abs/E01_x) 된다.
    상대 경로는 cwd → EPISODES_DIR → 저장소 루트 순으로 본다. 못 찾으면 찾아본 곳을 다 찍고 죽는다."""
    p = pathlib.Path(arg).expanduser()
    tried = [p] if p.is_absolute() else [pathlib.Path.cwd()/p, EPISODES_DIR/p, CHANNEL/p]
    for c in tried:
        if c.is_dir(): return c.resolve()
    seen, where = set(), []
    for c in tried:                                   # 같은 경로가 두 번 나오면(예: cwd 가 저장소 루트) 한 번만 보여준다
        r = str(c.resolve())
        if r not in seen: seen.add(r); where.append("  " + r)
    die(f"에피소드 폴더 없음: {arg}\n  찾아본 곳:\n" + "\n".join(where) +
        f"\n  있는 에피소드: {', '.join(sorted(d.name for d in EPISODES_DIR.iterdir() if d.is_dir())) if EPISODES_DIR.is_dir() else '(' + str(EPISODES_DIR) + ' 가 없습니다)'}")

def slug(ep: pathlib.Path) -> str:
    return ep.name.split("_")[0].lower()     # E06_popfilter -> e06

def P(ep):
    """자주 쓰는 경로 묶음"""
    return dict(
        scenes_v1 = ep/"script"/"scenes_v1.json",
        scenes_v2 = ep/"script"/"scenes_v2.json",
        caps_whisper = ep/"script"/"captions_whisper.json",
        caps = ep/"script"/"captions.json",
        caps_en = ep/"script"/"captions_en.json",
        overrides = ep/"script"/"tts_overrides.json",
        chapters = ep/"script"/"chapters.json",
        visual_prep = ep/"script"/"visual_prep.json",
        timing = ep/"script"/"timing.json",
        tts_input = ep/"audio"/"narration_tts_input.json",
        nar_raw = ep/"audio"/"nar_raw",
        nar_final = ep/"audio"/"narration_final",
        bounds = ep/"audio"/"nar_raw"/"speech_bounds.json",
        bounds_override = ep/"audio"/"bounds_override.json",
        cer = ep/"audio"/"nar_raw"/"whisper_cer.json",
        edit = ep/"edit",
    )

def jload(p): return json.load(open(p, encoding="utf-8"))

def script_sha(text: str) -> str:
    """대본 한 씬의 지문. 공백만 다른 것은 같은 것으로 본다(줄바꿈을 고쳐도 안 걸리게)."""
    return hashlib.sha1(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()[:12]


def script_drift(paths, made: dict) -> list:
    """음성·자막이 **어느 판본으로 만들어졌나.**

    30·40 은 `tts_input` 과 받아쓰기를 대조하는데 **둘 다 옛것이면 서로 맞는다** —
    대본이 뒤로 움직이면 검사도 같이 움직여서 어긋남이 안 보인다.
    실제로 그랬다: 대본을 고친 뒤에도 옛 음성이 CER 0.000 으로 통과했고, 잡은 것은 자막이었다.

    `source_md` 로는 안 된다. 이름은 안 바뀌면서 안에서 두 번 고쳐졌다.
    파일 시각도 눈치채야 보이는 것이라 안 된다. **씬별 지문이라야 놓치지 않는다.**

    `made` 는 씬 id → 만들 때의 지문. 반환은 지금 대본과 다른 씬 목록.
    """
    if not made: return []
    now = {s["id"]: script_sha(s["narration"]) for s in jload(paths["scenes_v1"])["scenes"]}
    return [sid for sid, h in sorted(made.items()) if sid in now and now[sid] != h]


def prep_entry(v):
    """visual_prep 의 clips/images 한 항목. 문자열이면 파일 이름만, 객체면 그대로.

    객체 꼴 — {"src": "raw.mp4", "ss": 0, "t": 9.192, "audio": true, "mask": [[x,y,w,h], ...]}
    `mask` 는 0~1 정규화 사각형이고 검게 덮는다. 좌표는 미술이 정한다.
    """
    return {"src": v} if isinstance(v, str) else dict(v)

def timing_of(paths, ids):
    """**내레이션이 정하지 않는 시각표 값들.** 없으면 빈 것을 돌려준다.

    씬 길이는 원래 내레이션으로만 정해진다(`LEAD + 내레이션 + GAP`). 그런데 화면이 길이를
    정해야 하는 자리가 있다 — 내레이션이 아예 없는 구간(훅으로 통 재생하는 클립)과,
    내레이션보다 영상이 긴 씬이다. 둘을 한 파일에 모은다.

        {
          "inserts": [ {"before": "s00", "items": [{"sec": 9.192, "clip": "intro_orig"}, …]},
                       {"after":  "s18", "items": [{"sec": 3.5,   "clip": "tail_m3"}]} ],
          "min_sec": { "s03": 21.4 }
        }

    `items` 의 `clip` 이 없으면 그 초만큼 화면이 빈다. `min_sec` 은 **씬 슬롯의 하한**이고
    내레이션이 그보다 길면 내레이션이 이긴다.

    반환: (before, after, min_sec, transition).
    `transition` 은 씬 사이 전환 길이(초). **시각표는 이 값으로 안 바뀐다** — 앞 것의 자리를
    그만큼 늘려 겹치고 들어오는 것이 그동안 움직인다. `TransitionSeries` 처럼 겹친 만큼
    전체를 줄이면 소리와 어긋나고, 32곳에서 누적되는데 렌더는 안 죽는다.
    """
    f = paths["timing"]
    if not f.exists(): return {}, {}, {}, {"default": 0.0, "after": {}}
    d = jload(f)
    before, after = {}, {}
    for i, ins in enumerate(d.get("inserts") or [], 1):
        items = ins.get("items") or []
        if not items: die(f'{f}: {i}번째 insert 에 items 가 없습니다', 2)
        for j, it in enumerate(items, 1):
            if not isinstance(it.get("sec"), (int, float)) or it["sec"] <= 0:
                die(f'{f}: {i}번째 insert 의 {j}번째 항목에 sec(초)가 없습니다 — {it}', 2)
        where = [k for k in ("before", "after") if k in ins]
        if len(where) != 1:
            die(f'{f}: {i}번째 insert 는 before 나 after 중 하나만 있어야 합니다 — {ins}', 2)
        sid = ins[where[0]]
        if sid not in ids:
            die(f'{f}: {i}번째 insert 의 {where[0]} "{sid}" 는 없는 씬입니다. 있는 씬: {", ".join(ids)}', 2)
        (before if where[0] == "before" else after).setdefault(sid, []).extend(items)
    mn = d.get("min_sec") or {}
    for sid in mn:
        if sid not in ids: die(f'{f}: min_sec 의 "{sid}" 는 없는 씬입니다', 2)
        if not isinstance(mn[sid], (int, float)) or mn[sid] <= 0:
            die(f'{f}: min_sec["{sid}"] 가 초가 아닙니다 — {mn[sid]}', 2)
    tr = d.get("transition") or {}
    return before, after, mn, {"default": float(tr.get("default", 0.0)), "after": {k: float(v) for k, v in (tr.get("after") or {}).items()}}

def jdump(obj, p, indent=1):
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=indent)

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def dur(f) -> float:
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(f)]).decode())

def clipped(f) -> int:
    """풀스케일(|x| >= 1.0) 이상 샘플 수. ebur128 의 Peak 은 dBFS 로 반올림돼 -0.0 과 0.0 이 안 갈린다 —
    클리핑 판정은 이 수로 한다. docs/RECORDING.md 의 참조 음성 검산과 같은 기준이다."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-f", "f32le", "-"],
                         capture_output=True).stdout
    if not raw: return 0
    x = np.frombuffer(raw, dtype="<f4")
    return int((abs(x) >= 1.0).sum())

def lufs(f):
    out = subprocess.run(["ffmpeg","-i",str(f),"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
    I = re.findall(r"I:\s+(-?[0-9.]+) LUFS", out); Pk = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", out)
    return (float(I[-1]) if I else None, float(Pk[-1]) if Pk else None)

# ---------- 텍스트 ----------
norm = lambda s: re.sub(r'[\s\.,\?!"“”\'\-·~…:;()\[\]]', "", s)

SINO = "영일이삼사오육칠팔구"
def sino(n: int) -> str:
    """정수 → 한자어 숫자 읽기 (0~99999)"""
    if n == 0: return "영"
    units = [("만",10000),("천",1000),("백",100),("십",10)]
    out = ""
    for name, v in units:
        d = n // v; n %= v
        if d: out += ("" if d == 1 and v < 10000 else SINO[d]) + name
    if n: out += SINO[n]
    return out

NATIVE_TENS = {10:"열",20:"스물",30:"서른",40:"마흔",50:"쉰",60:"예순",70:"일흔",80:"여든",90:"아흔"}
NATIVE_UNIT = ["","한","두","세","네","다섯","여섯","일곱","여덟","아홉"]
NATIVE_COUNTERS = ("개","번","명","장","마디","살","시간","컷","편","군데","줄","가지","벌","곳","시")
def native(n: int) -> str:
    # 고유어 수사에 0 이 없다. NATIVE_UNIT[0] 이 빈 문자열이라 그냥 두면 숫자가 통째로 사라진다
    # ('0개' → ' 개'). 0 은 한자어로 떨어뜨린다: 영 개, 영 컷.
    if n == 0: return SINO[0]
    if n >= 100: return sino(n)
    t, u = (n//10)*10, n%10
    if n == 20 and u == 0: return "스무"
    return (NATIVE_TENS.get(t, "") + NATIVE_UNIT[u]) if n >= 10 else NATIVE_UNIT[u]

DIGITS = "영일이삼사오육칠팔구"

def read_number(m):
    """숫자를 한글 읽기로. 소수는 '영 점 삼 오' 처럼 점 뒤를 한 자리씩 **띄어서** 읽는다.
    앞에 붙은 빼기표(-, −)는 '마이너스'로 읽는다: −16 → 마이너스 십육"""
    r, unit = read_number_parts(m)
    return r + (" " + unit if unit else "")

def read_number_parts(m):
    """(숫자 읽기, 뒤에 붙은 단위·조사). 30단계의 숫자 완전일치는 **숫자 읽기만** 본다 —
    단위·조사까지 묶으면 '초'가 '추'로 들린 것 같은 뒤 글자 오독이 숫자 오독으로 잡힌다(E01 s15).
    그쪽은 CER 과 big_diffs 가 본다."""
    num, unit = m.group(1), m.group(2)
    sign = ""
    if num[0] in "-\u2212":
        sign, num = "마이너스 ", num[1:]
    if "." in num:
        # 0.35초 → 영 점 삼 오 초 (소수는 항상 한자어, 소수부는 자릿수 그대로)
        # 붙여 쓰면 자음동화로 자릿수가 무너진다 — 9.167 의 '일육'[일륙]이 [이륙]으로 들려 9.267 이 됐다(E01 실측).
        # 정수부는 안 띄운다. '백십팔'은 자릿값 읽기라 띄우면 뜻이 깨진다.
        head, frac = num.split(".", 1)
        # 끝의 0 은 읽지 않는다: 0.80 → 영 점 팔. 가운데·앞의 0 은 자릿값이라 남긴다(0.801, 0.025).
        frac = "".join(c for c in frac if c.isdigit()).rstrip("0")
        if frac:
            n = int(head.replace(",", "")) if head else 0
            return sign + sino(n) + " 점 " + " ".join(DIGITS[int(c)] for c in frac), unit
        num = head or "0"            # 소수부가 전부 0 이면 정수로 읽는다: 2.00초 → 이 초
    n = int(num.replace(",", ""))
    if unit and unit.startswith(NATIVE_COUNTERS) and not unit.startswith("시간") and unit != "시간":
        return sign + native(n), unit
    return sign + sino(n), unit

EMPH = re.compile(r"\*\*(.+?)\*\*")

def strip_emphasis(t: str) -> str:
    """대본의 **강조** 표시를 지운다. 음성에는 표시가 가면 안 된다."""
    return EMPH.sub(r"\1", t)

def split_emphasis(t: str):
    """**강조** 를 (글자, 강조여부) 조각들로 나눈다. 자막이 쓴다."""
    out, i = [], 0
    for m in EMPH.finditer(t):
        if m.start() > i: out.append((t[i:m.start()], False))
        out.append((m.group(1), True)); i = m.end()
    if i < len(t): out.append((t[i:], False))
    return out or [(t, False)]

NUM = re.compile(r"([-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-−]?\d+(?:\.\d+)?)\s*([가-힣]+)?")
# 단위 낱말. 뒤에 붙은 조사를 떼려고 쓴다: '명과' → '명', '초짜리를' → '초'
UNIT_WORDS = tuple(sorted(set(NATIVE_COUNTERS + ("초","분","회","건","프레임","센티미터","밀리미터",
             "미터","퍼센트","배","도","자","단계","비트","글자","픽셀","킬로바이트")), key=len, reverse=True))

def unit_head(unit: str) -> str:
    """단위 문자열에서 단위 한 낱말만 떼어 낸다. 모르는 단위면 첫 글자만 쓴다 —
    앞자락이라 대조(부분 문자열 찾기)에 그대로 쓸 수 있다('프'는 '프레임'의 앞자락)."""
    for u in UNIT_WORDS:
        if unit.startswith(u): return u
    return unit[:1]
RANGE = re.compile(r"(?<=\d)\s*[~〜～–-]\s*(?=\d)")     # 숫자 사이의 물결표·붙임표 = 범위. 숫자 **앞**의 -는 마이너스라 안 걸린다
DASH = re.compile(r"\s*—\s*")                          # 줄표는 쉼을 뜻한다. TTS 는 그냥 무시하고 이어 읽는다(E01 실측)
# 소리로 나갈 수 있는 글자. 이 밖의 것이 남으면 10단계가 멈춘다 — 기호를 사전으로 하나씩 막으면 다음 편에서 샌다
SPEAKABLE = re.compile(r"[가-힣0-9 .,?!]")

def tts_preprocess(text: str, readings: dict):
    """숫자·영문·기호를 한글 읽기로.
    반환: (전처리문, 사전에 없는 영문 토큰, 소리로 못 내는 문자, 무엇을 무엇으로 바꿨는지)
    subs 한 항목: {"kind": "reading|range|dash|number", "from": 원문, "to": 읽기}
    number 항목은 30단계가 받아쓰기와 완전일치로 대조한다(CER 로는 한 자리 오독을 못 잡는다)."""
    t, subs = strip_emphasis(text), []

    def record(kind, frm, to):
        subs.append({"kind": kind, "from": frm, "to": to}); return to

    for k in sorted(readings, key=len, reverse=True):
        if k.startswith("_"): continue
        t = re.sub(r"(?<![A-Za-z])" + re.escape(k) + r"(?![A-Za-z])",
                   lambda m, v=readings[k]: record("reading", m.group(0), v), t)
    t = RANGE.sub(lambda m: record("range", m.group(0), " 에서 "), t)
    t = DASH.sub(lambda m: record("dash", m.group(0), ", "), t)
    def _num(m):
        r, unit = read_number_parts(m)
        full = r + (" " + unit if unit else "")
        # 숫자 읽기가 한 글자면 뒤 단위 한 낱말까지 붙인다. '이'·'일'·'사'는 한국어 문장에 지천이라
        # 그 한 글자만으로는 엉뚱한 자리에 걸린다 — '2.00초 → 이'가 5글자 앞의 '시각이'에 걸렸다(E01 s10).
        # 조사는 뺀다. 붙이면 '초'가 '추'로 들린 것 같은 뒤 글자 오독까지 숫자 오독이 된다(s15).
        num = r + (" " + unit_head(unit) if unit and len(norm(r)) == 1 else "")
        subs.append({"kind": "number", "from": m.group(0), "to": full, "num": num})   # num = 30단계 대조용
        return full
    t = NUM.sub(_num, t)

    left = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9/\-]*", t)))
    # 영문 글자는 left 로 따로 보고하므로 여기서 뺀다
    bad = sorted({c for c in t if not SPEAKABLE.match(c) and not (c.isascii() and c.isalpha())})
    return t, left, bad, subs

def big_diffs(ref: str, hyp: str, min_len=4):
    """정규화 문자열 비교. 반환 (cer, [(ref조각,hyp조각), ...] 길이 min_len 이상만). 3자 이하는 whisper 오타 대역이라 무시."""
    R, H = norm(ref), norm(hyp)
    sm = difflib.SequenceMatcher(None, R, H)
    err = sum(max(i2-i1, j2-j1) for t,i1,i2,j1,j2 in sm.get_opcodes() if t != "equal")
    big = [(R[i1:i2], H[j1:j2]) for t,i1,i2,j1,j2 in sm.get_opcodes() if t != "equal" and (i2-i1 >= min_len or j2-j1 >= min_len)]
    return round(err/max(1,len(R)), 3), big

# ---------- whisper ----------
_wm = None
def whisper_model():
    global _wm
    if _wm is None:
        import whisper; _wm = whisper.load_model(WHISPER_MODEL)
    return _wm

def transcribe(f, words=False):
    r = whisper_model().transcribe(str(f), language="ko", fp16=False, word_timestamps=words)
    ws = [w for seg in r["segments"] for w in seg.get("words", [])] if words else []
    return r["text"], ws

def hyp_normalize_readings(hyp: str, readings: dict) -> str:
    """whisper가 숫자/영문으로 받아쓴 것을 대본 전처리문과 같은 읽기로 맞춘다."""
    h = hyp
    for k in sorted(readings, key=len, reverse=True):
        if k.startswith("_"): continue
        # 키 안의 구분자(/, 공백)는 받아쓰기에서 쉼표·점·공백으로 나올 수 있다: "A/B" ↔ "A, B"
        pat = re.escape(k).replace(r"/", r"[\s,./\-]*").replace(r"\ ", r"[\s,./\-]*")
        h = re.sub(r"(?<![A-Za-z])" + pat + r"(?![A-Za-z])", readings[k], h, flags=re.I)
    h = re.sub(r"([-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-−]?\d+(?:\.\d+)?)\s*([가-힣]+)?", read_number, h)
    return h

# ---------- 원격 ComfyUI ----------
class Comfy:
    def __init__(self, host): self.host = host.rstrip("/")
    def _get(self, path):
        return json.loads(urllib.request.urlopen(self.host + path, timeout=30).read())
    def alive(self):
        try: self._get("/system_stats"); return True
        except Exception: return False
    def upload_input(self, path):
        run(["curl","-s","-m","60","-F",f"image=@{path}","-F","type=input","-F","overwrite=true",self.host+"/upload/image"],stdout=subprocess.DEVNULL)
    def submit(self, wf):
        req = urllib.request.Request(self.host+"/prompt", data=json.dumps({"prompt": wf}).encode(), headers={"Content-Type":"application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if r.get("node_errors"): die("ComfyUI node_errors: " + json.dumps(r["node_errors"])[:500])
        return r["prompt_id"]
    def wait(self, pid, timeout=900, poll=3):
        t0 = time.time()
        while time.time()-t0 < timeout:
            h = self._get(f"/history/{pid}")
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error": raise RuntimeError("ComfyUI job error: " + json.dumps(st)[:500])
                if h[pid].get("outputs"): return h[pid]
            time.sleep(poll)
        raise TimeoutError(pid)
    def audio_files(self, hist):
        return [f for o in hist.get("outputs", {}).values() for f in o.get("audio", [])]
    def download(self, f, out):
        url = self.host + f"/view?filename={f['filename']}&subfolder={f.get('subfolder','')}&type={f.get('type','output')}"
        open(out, "wb").write(urllib.request.urlopen(url, timeout=120).read())
    @staticmethod
    def exec_secs(hist):
        ts = {m[0]: m[1].get("timestamp") for m in hist["status"].get("messages", []) if isinstance(m, list) and len(m) > 1 and isinstance(m[1], dict)}
        s, e = ts.get("execution_start"), ts.get("execution_success") or ts.get("execution_error")
        return round((e-s)/1000, 1) if s and e else None

def voice_cfg():
    f = VOICE_DIR/"voice.json"
    if not f.exists():
        die(f"목소리 설정이 없습니다: {f}\n  cp pipeline/voice.example.json pipeline/voice.json 로 만든 뒤 고치세요.", 2)
    return jload(f)

def provider_name(cfg) -> str:
    """voice.json 의 provider 이름."""
    name = cfg.get("provider")
    if not name:
        die('voice.json 에 "provider" 가 없습니다. voice.example.json 을 보고 채우세요.', 2)
    return name

def provider_cfg(cfg, name=None) -> dict:
    """voice.json 의 providers[<이름>] 블록. 어댑터가 받는 cfg 는 항상 이것이다."""
    name = name or provider_name(cfg)
    blocks = cfg.get("providers")
    if not isinstance(blocks, dict) or name not in blocks:
        have = ", ".join(blocks) if isinstance(blocks, dict) else "(없음)"
        die(f'voice.json 의 providers 에 "{name}" 블록이 없습니다. 있는 블록: {have}', 2)
    return blocks[name]

def _provider_module(name):
    import providers as _providers                     # pipeline/providers
    if name not in _providers.REGISTRY:
        die(f"모르는 제공자: {name}. 가능한 값: {', '.join(_providers.REGISTRY)}", 2)
    return _providers.get(name)

def tts_generate(text, out_path, cfg, attempt=0, host=None):
    """한 문장을 음성으로. cfg 는 voice.json **전체**를 넘긴다(제공자 선택을 여기서 한다).
    어댑터에는 providers[<이름>] 블록만 간다. 반환: 생성에 걸린 초 (모르면 None)."""
    name = provider_name(cfg)
    mod = _provider_module(name)
    kw = {}
    if host is not None:
        import inspect
        if "host" not in inspect.signature(mod.generate).parameters:
            die(f"제공자 {name} 은 서버 주소를 받지 않습니다(--host 는 comfyui_chatterbox 전용).", 2)
        kw["host"] = host
    return mod.generate(text, str(out_path), provider_cfg(cfg, name), attempt=attempt, **kw)

def pick_ids(arg, known, what="씬"):
    """--ids 문자열 → 집합. **안 주면** None(전체).
    없는 id 를 주면 조용히 0건 처리하지 않고 죽는다.

    **빈 값과 안 준 값을 가른다.** `if not arg` 로 쓰면 `--ids ""` 가 「전체」가 되어
    한 씬만 돌리려던 것이 29씬을 다 돈다 — 스크립트로 묶을 때 변수가 비면 그렇게 된다.
    (같은 자리를 `65_render_derived.sh` 의 `${3:-1,2}` 에서 실제로 밟았다.)"""
    if arg is None: return None
    ids = [x.strip() for x in arg.split(",") if x.strip()]
    if not ids: die("--ids 가 비어 있습니다. 전체를 돌리려면 --ids 를 **아예 주지 마세요**.", 2)
    unknown = [i for i in ids if i not in known]
    if unknown:
        die(f"--ids 에 없는 {what}: {', '.join(unknown)}\n  있는 것: {', '.join(sorted(known))}", 2)
    return set(ids)

def upload_ref(comfy, v):
    """채널 참조 음성을 노드가 기대하는 이름(ref_upload_name)으로 원격 input 폴더에 올린다(덮어쓰기)."""
    src = VOICE_DIR / v["ref_file"]
    if not src.exists(): die(f"참조 음성 없음: {src}")
    import shutil, tempfile
    tmp = pathlib.Path(tempfile.gettempdir()) / v["ref_upload_name"]; shutil.copy(src, tmp); comfy.upload_input(tmp)

def chatterbox_wf(text, prefix, v, seed=None, temperature=None):
    return {"1": {"class_type":"LoadAudio","inputs":{"audio": v["ref_upload_name"]}},
            "2": {"class_type": v["node"], "inputs": {"text": text, "language": v["language"], "exaggeration": v["exaggeration"],
                  "cfg_weight": v["cfg_weight"], "temperature": temperature if temperature is not None else v["temperature"],
                  "repetition_penalty": v["repetition_penalty"], "min_p": v["min_p"], "top_p": v["top_p"],
                  "seed": seed if seed is not None else v["seed"], "audio_prompt": ["1",0], "use_cpu": False, "keep_model_loaded": True}},
            "3": {"class_type":"SaveAudioMP3","inputs":{"audio":["2",0],"filename_prefix":prefix,"quality":"V0"}}}

def tts_one(comfy, v, text, prefix, out, seed=None, temperature=None):
    """한 씬 생성 → out 경로 저장, 실행 초 반환"""
    pid = comfy.submit(chatterbox_wf(text, prefix, v, seed, temperature))
    hist = comfy.wait(pid)
    files = comfy.audio_files(hist)
    if not files: raise RuntimeError("no audio output " + pid)
    comfy.download(files[0], out)
    return Comfy.exec_secs(hist)

def whisper_fixes_for(ep):
    r = jload(PIPE_DIR/"whisper_fixes.json"); f = ep/"script"/"whisper_fixes.json"
    if f.exists(): r.update(jload(f))
    return {k: v for k, v in r.items() if not k.startswith("_")}

def check_scene(f, ref_text, readings, fixes=None, num_tokens=None):
    """whisper 검사 한 씬. num_tokens 는 전처리가 숫자에서 만든 읽기들(10단계의 subs).
    반환 dict(cer, big, kind, text, hyp, num_missing, first_word, last_word_end, suggest_last_word_end, tail_insert, dur)
    kind: 'ok' | 'tail'(끝에만 없는 문장이 붙음 = 꼬리 잡음, 트림 대상) | 'content'(누락·반복·오독, 재생성 대상)

    content 로 올리는 조건 셋 (OR)
    - big_diffs 가 잡은 내용 차이 (지금까지의 판정)
    - **숫자 읽기가 하나라도 안 들림** — CER 로는 못 잡는다. 118자 문장에서 한 글자는 0.013 이고,
      그만큼 조이면 정상 씬(최대 0.054 실측)이 먼저 걸린다
    - **CER > CER_MAX** — 값을 출력만 하고 판정에 안 쓰던 것을 실제로 쓴다"""
    text, ws = transcribe(f, words=True)
    hyp = text
    for k, v in (fixes or {}).items(): hyp = hyp.replace(k, v)
    hyp = hyp_normalize_readings(hyp, readings)
    cer, big = big_diffs(ref_text, hyp)
    d = dur(f)
    # 꼬리 삽입 탐지: 단어열 기준으로 정렬해 ref가 끝난 뒤에 붙은 hyp 텍스트를 찾는다
    R = norm(ref_text); wn = [norm(w["word"]) for w in ws]; Hw = "".join(wn)
    tail_insert, suggest = "", None
    if ws:
        ops = difflib.SequenceMatcher(None, R, Hw).get_opcodes()
        t, i1, i2, j1, j2 = ops[-1]
        if t == "insert" and i1 == len(R) and j2 - j1 >= 3:
            tail_insert = Hw[j1:j2]
            acc = 0
            for k, w in enumerate(wn):
                acc += len(w)
                if acc >= j1:
                    # whisper 단어 끝은 끄는 소리에서 일찍 끊기므로 0.4s 여유, 단 잡음 첫 단어 시작은 넘지 않는다
                    prev_end = ws[k-1]["end"] if k > 0 else 0.0
                    suggest = round(min(prev_end + 0.4, ws[k]["start"]), 2); break
    content = [b for b in big if b[0] != ""] or ([b for b in big if b[0] == "" and norm(b[1]) not in tail_insert])
    # 숫자는 완전일치로 본다. 공백·문장부호 차이는 무시하려고 양쪽 다 norm 을 거친다.
    # 대본에 나온 **순서대로** 찾는다 — 앞 토큰이 쓴 자리 뒤에서만 다음 토큰을 본다.
    # '영' 처럼 한 글자짜리 읽기가 앞쪽 다른 숫자('십 점 영 사')의 일부에 걸려 통과하는 것을 막는다.
    H, cur, num_missing = norm(hyp), 0, []
    for tok in (num_tokens or []):
        n = norm(tok)
        if not n: continue
        i = H.find(n, cur)
        if i < 0: num_missing.append(tok)      # 못 찾으면 커서는 그대로 둔다(뒤 토큰까지 연달아 걸리지 않게)
        else: cur = i + len(n)
    kind = "content" if (content or num_missing or cer > CER_MAX) else ("tail" if tail_insert else "ok")
    return {"cer": cer, "big": big, "kind": kind, "text": text, "hyp": hyp, "num_missing": num_missing,
            "first_word": round(ws[0]["start"],2) if ws else 0.0,
            "last_word_end": round(ws[-1]["end"],2) if ws else d, "suggest_last_word_end": suggest, "tail_insert": tail_insert,
            "last_words": "".join(w["word"] for w in ws[-3:]), "dur": round(d,2)}

def readings_for(ep):
    r = jload(PIPE_DIR/"tts_readings.json")
    ov = P(ep)["overrides"]
    if ov.exists(): r.update(jload(ov))
    return r
