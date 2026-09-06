"""채널 공정 공통 모듈. 모든 단계 스크립트가 이 파일만 import한다.
경로 규약: <EP>/script, <EP>/audio, <EP>/edit, <EP>/source  (EP = episodes/E01_myepisode 같은 에피소드 폴더)
"""
import json, os, re, subprocess, sys, time, pathlib, urllib.request, difflib

PIPE_DIR = pathlib.Path(__file__).resolve().parent               # .../pipeline
ROOT = PIPE_DIR.parent                                           # 저장소 루트
EPISODES_DIR = pathlib.Path(os.environ.get("EPISODES_DIR", ROOT / "episodes"))
# Remotion 프로젝트 위치: 환경변수 REMOTION_DIR > 저장소 옆 remotion/ > 오류
def _remotion_dir():
    env = os.environ.get("REMOTION_DIR")
    if env: return pathlib.Path(env).expanduser()
    here = pathlib.Path(__file__).resolve().parent.parent / "remotion"
    if here.is_dir(): return here
    return pathlib.Path("remotion")
REMOTION_DIR = _remotion_dir()

# 타이밍·음량 상수 (실측으로 확정된 기본값)
LEAD = 0.5        # 씬 시작 후 내레이션 시작까지
GAP = 0.8         # 내레이션 끝 후 씬 끝까지
PAD = 0.35        # 마지막 단어 끝 + PAD 에서 트림
FADE = 0.08       # 트림 직전 페이드아웃
NAR_LUFS = -16    # 씬 단위 내레이션
MASTER_LUFS = -14 # 최종 마스터
BGM_LUFS = -27    # 배경음악
CER_MAX = 0.06    # 씬 단위 글자 오류율 상한(전처리 후 기준, 정보용)
WHISPER_MODEL = "medium"

def die(msg, code=1):
    print("ERROR:", msg, file=sys.stderr); sys.exit(code)

def ep_dir(arg) -> pathlib.Path:
    p = pathlib.Path(arg).expanduser()
    if not p.is_absolute():
        for base in (pathlib.Path.cwd(), ROOT, EPISODES_DIR):
            cand = base / p
            if cand.is_dir(): p = cand.resolve(); break
        else: p = (pathlib.Path.cwd() / p).resolve()
    if not p.is_dir(): die(f"에피소드 폴더 없음: {p}")
    return p

def slug(ep: pathlib.Path) -> str:
    return ep.name.split("_")[0].lower()     # E01_myepisode -> e01

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
        tts_input = ep/"audio"/"narration_tts_input.json",
        nar_raw = ep/"audio"/"nar_raw",
        nar_final = ep/"audio"/"narration_final",
        bounds = ep/"audio"/"nar_raw"/"speech_bounds.json",
        bounds_override = ep/"audio"/"bounds_override.json",
        cer = ep/"audio"/"nar_raw"/"whisper_cer.json",
        edit = ep/"edit",
    )

def jload(p): return json.load(open(p, encoding="utf-8"))
def jdump(obj, p, indent=1):
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=indent)

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def dur(f) -> float:
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(f)]).decode())

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
    if n >= 100: return sino(n)
    t, u = (n//10)*10, n%10
    if n == 20 and u == 0: return "스무"
    return (NATIVE_TENS.get(t, "") + NATIVE_UNIT[u]) if n >= 10 else NATIVE_UNIT[u]

def read_number(m):
    num, unit = m.group(1), m.group(2)
    n = int(num.replace(",", ""))
    if unit and unit.startswith(NATIVE_COUNTERS) and not unit.startswith("시간") and unit != "시간":
        return native(n) + " " + unit
    return sino(n) + (" " + unit if unit else "")

def tts_preprocess(text: str, readings: dict) -> tuple[str, list]:
    """숫자·영문을 한글 읽기로. 반환: (전처리문, 사전에 없는 영문 토큰 목록)"""
    t = text
    for k in sorted(readings, key=len, reverse=True):
        if k.startswith("_"): continue
        t = re.sub(r"(?<![A-Za-z])" + re.escape(k) + r"(?![A-Za-z])", readings[k], t)
    t = re.sub(r"(\d[\d,]*)\s*([가-힣]+)?", read_number, t)
    left = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9/\-]*", t)))
    return t, left

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
    h = re.sub(r"(\d[\d,]*)\s*([가-힣]+)?", read_number, h)
    return h

def voice_cfg():
    """pipeline/voice.json 을 읽는다. 없으면 voice.example.json 을 복사하라고 알린다."""
    p = PIPE_DIR/"voice.json"
    if not p.exists():
        die(f"{p} 가 없습니다.\n  cp pipeline/voice.example.json pipeline/voice.json  후 편집하세요.")
    v = jload(p)
    name = v.get("provider")
    if not name:
        die("voice.json 에 provider 가 없습니다. 예: \"provider\": \"comfyui_chatterbox\"")
    blocks = v.get("providers", {})
    if name not in blocks:
        die(f"voice.json 의 providers 에 '{name}' 블록이 없습니다.")
    cfg = dict(blocks[name]); cfg["_provider"] = name
    return cfg


def tts_generate(text, out_path, cfg, attempt=0):
    """설정된 제공자로 문장 하나를 음성으로. 반환: 생성 초(모르면 None).
    제공자를 바꾸려면 voice.json 의 provider 만 바꾸면 된다 — 나머지 공정은 그대로다."""
    import sys as _sys
    if str(PIPE_DIR) not in _sys.path: _sys.path.insert(0, str(PIPE_DIR))
    import providers
    return providers.get(cfg["_provider"]).generate(text, str(out_path), cfg, attempt=attempt)


def readings_for(ep):
    r = jload(PIPE_DIR/"tts_readings.json")
    ov = P(ep)["overrides"]
    if ov.exists(): r.update(jload(ov))
    return r
