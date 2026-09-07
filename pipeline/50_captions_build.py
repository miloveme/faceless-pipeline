#!/usr/bin/env python3
"""최종 wav에 whisper 단어 타임스탬프를 돌려 청크를 만들고(captions_whisper.json),
원문 대본 문장을 그 낱말 시각에 정렬해 captions.json을 만든다.
자막 텍스트는 항상 원문(숫자·영문 표기 그대로)이고 whisper 받아쓰기는 타이밍에만 쓴다.

줄 경계는 받아쓰기 청크 경계가 아니라 **낱말 시각**으로 잡는다.
청크는 38자에서 끊고 대본 문장은 마침표·쉼표에서 끊어 둘이 안 맞는데,
개수만 같으면 1:1로 붙이던 탓에 앞줄이 시간을 다 먹고 뒷줄에 꼬리만 남았다.
사용: 50_captions_build.py <EP> [--ids ...]"""
import argparse, bisect
from common import *

# 읽기 속도 기준 — 자막·음악 감독 영역의 값이다. 엔지니어가 혼자 바꾸지 않는다.
CPS_MAX = 15.0    # 상한. 넘는 줄이 남으면 종료코드 3
CPS_OK = 12.0     # 편한 속도(8~12 cps)의 위쪽 끝 — 보고용
MIN_DUR = 1.2     # 한 줄 최소 노출(초)

ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default=""); ap.add_argument("--maxlen", type=int, default=42)
ap.add_argument("--emph-only", dest="emph_only", action="store_true",
                help="대본의 **강조** 표시만 기존 자막에 다시 반영한다(받아쓰기 건너뜀). "
                     "강조는 대본에서 나오므로 음성을 다시 들을 이유가 없다.")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
if not p["scenes_v2"].exists(): die(f"씬 시각표가 없습니다: {p['scenes_v2']}\n  먼저 40_nar_finalize.py 를 돌리세요.")
sc = jload(p["scenes_v2"]); only = pick_ids(a.ids, {s["id"] for s in sc["scenes"]})
targets = [s for s in sc["scenes"] if not only or s["id"] in only]
wc = jload(p["caps_whisper"]) if p["caps_whisper"].exists() else {}
caps = jload(p["caps"]) if p["caps"].exists() else {}
def sentences(t):
    out = []
    for s in re.split(r"(?<=[\.\?!])\s+", t.strip()):
        s = s.strip()
        if not s: continue
        if len(s) > a.maxlen and "," in s:
            i = s.rfind(",", 0, len(s)//2 + 8)
            if i > 10: out += [s[:i+1].strip(), s[i+1:].strip()]; continue
        out.append(s)
    return out

def emph_flags(raw: str):
    """원문 조각을 낱말 단위 강조 여부로 편다."""
    flags = []
    for seg, on in split_emphasis(raw):
        for w in seg.split():
            flags.append(on)
    return flags

# ---------- 낱말 시각으로 줄 경계 잡기 ----------
def _hyp_chars(ws):
    """받아쓰기 낱말들 → (정규화 글자열, 낱말 시작 글자위치표 len(ws)+1개)"""
    s = ""; pos = [0]
    for w in ws:
        s += norm(w["word"]); pos.append(len(s))
    return s, pos

def _ref_chars(lines):
    """원문 줄들 → (정규화 글자열, 줄 경계 위치표, 줄별 토큰 경계 위치표)"""
    s = ""; bnd = [0]; toks = []
    for ln in lines:
        tb = [len(s)]
        for t in ln.split():
            s += norm(t); tb.append(len(s))
        toks.append(tb); bnd.append(len(s))
    return s, bnd, toks

def _mapper(ref, hyp):
    """원문 글자위치 → 받아쓰기 글자위치. 일치 블록 안은 1:1, 블록 사이는 비례.
    받아쓰기는 대본과 글자가 다르므로(Chatterbox↔채터박스) 문자열 정렬로 이어 준다."""
    blocks = difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_matching_blocks()
    def f(q):
        pr, ph = 0, 0
        for i, j, n in blocks:
            if q < i:
                return ph + (j - ph) * (q - pr) / (i - pr) if i > pr else float(ph)
            if q < i + n: return float(j + (q - i))
            pr, ph = i + n, j + n
        return float(ph)
    return f

def _htime(h, ws, wpos):
    """받아쓰기 글자위치 → 시각. 낱말 안에서는 비례 보간."""
    h = max(0.0, min(float(h), float(wpos[-1])))
    k = min(max(bisect.bisect_right(wpos, h) - 1, 0), len(ws) - 1)
    lo, hi = wpos[k], wpos[k + 1]
    s0, e0 = ws[k]["start"], ws[k]["end"]
    return s0 if hi <= lo else s0 + (e0 - s0) * (h - lo) / (hi - lo)

def _btime(k, ws):
    """낱말 k 앞에서 자를 때의 경계 시각 — 앞 낱말 끝과 다음 낱말 시작 사이 침묵의 한가운데."""
    if k <= 0: return ws[0]["start"]
    if k >= len(ws): return ws[-1]["end"]
    return (ws[k - 1]["end"] + ws[k]["start"]) / 2

def _fit(T, need, lo, hi):
    """경계를 최소한으로 밀어 각 줄이 need 초 이상 노출되게 한다.
    여유 있는 이웃에서만 시간을 가져오고, 씬 밖으로는 나가지 않는다."""
    n = len(need); tot = sum(need)
    if tot > hi - lo:                       # 공간 자체가 모자라다 — 비례로 나누고 아래 검사에서 잡힌다
        out = [lo]
        for x in need: out.append(out[-1] + (hi - lo) * x / tot)
        return out
    T = [min(max(t, lo), hi) for t in T]
    for i in range(n):                      # 앞→뒤: 모자라면 오른쪽 경계를 민다
        if T[i + 1] - T[i] < need[i]: T[i + 1] = T[i] + need[i]
    if T[n] > hi:                           # 끝을 넘겼으면 뒤→앞으로 되민다
        T[n] = hi
        for i in range(n - 1, -1, -1):
            if T[i + 1] - T[i] < need[i]: T[i] = T[i + 1] - need[i]
    return T

def align(lines, ws, d):
    """원문 줄 + 받아쓰기 낱말 → [(start, end, words)].
    낱말 시각이 없거나 낱말 수가 줄 수보다 적으면 글자 수 비례로 되돌린다."""
    n = len(lines)
    if not n: return []
    hyp, wpos = _hyp_chars(ws); ref, bnd, tokpos = _ref_chars(lines)
    ok = bool(ws) and len(ws) >= n and len(hyp) > 0 and len(ref) > 0
    lo = 0.0; hi = max(d, ws[-1]["end"] if ws else 0.0, MIN_DUR * n)
    f = _mapper(ref, hyp) if ok else None
    if ok:
        ks = [0]
        for i in range(1, n):
            h = f(bnd[i]); k = bisect.bisect_left(wpos, h)
            if k > 0 and (k >= len(wpos) or abs(wpos[k - 1] - h) <= abs(wpos[k] - h)): k -= 1
            ks.append(k)
        ks.append(len(ws))
        for i in range(1, n):               # 경계는 반드시 앞뒤 순서를 지킨다
            ks[i] = min(max(ks[i], ks[i - 1] + 1), len(ws) - (n - i))
        T = [_btime(k, ws) for k in ks]
    else:
        T = [lo + (hi - lo) * bnd[i] / max(1, bnd[-1]) for i in range(n + 1)]
    T = _fit(T, [max(MIN_DUR, len(t) / CPS_MAX) for t in lines], lo, hi)
    out = []
    for i, ln in enumerate(lines):
        toks = ln.split(); a0, b0 = T[i], T[i + 1]; wl = []
        if ok and toks:
            ts = [min(max(_htime(f(x), ws, wpos), a0), b0) for x in tokpos[i]]
            ts[0], ts[-1] = a0, b0
            for j in range(1, len(ts)): ts[j] = max(ts[j], ts[j - 1])
            wl = [{"s": round(ts[j], 2), "e": round(ts[j + 1], 2), "t": t} for j, t in enumerate(toks)]
        elif toks:
            tot = sum(len(t) for t in toks); acc = 0
            for t in toks:
                s0 = a0 + (b0 - a0) * acc / tot; acc += len(t)
                wl.append({"s": round(s0, 2), "e": round(a0 + (b0 - a0) * acc / tot, 2), "t": t})
        out.append((round(a0, 2), round(b0, 2), wl))
    return out

# ---------- 읽기 속도 검사 ----------
def cps_of(c):
    d0 = c["end"] - c["start"]
    return len(c["text"]) / d0 if d0 > 0 else 9999.0

def speed_report(caps, done, tail):
    """처리한 씬의 줄들을 재고, (위반목록, 마지막에 찍을 한 줄)을 준다."""
    rows = [(sid, i, c) for sid in done for i, c in enumerate(caps.get(sid, []))]
    bad = [r for r in rows if cps_of(r[2]) > CPS_MAX + 1e-6]
    slow = sum(1 for r in rows if cps_of(r[2]) > CPS_OK + 1e-6)
    shrt = sum(1 for r in rows if r[2]["end"] - r[2]["start"] < MIN_DUR - 1e-6)
    rest = sum(1 for sid, cc in caps.items() if sid not in done for c in cc if cps_of(c) > CPS_MAX + 1e-6)
    for sid, i, c in sorted(bad, key=lambda r: -cps_of(r[2])):
        print(f"  {sid} {i+1}번째 줄  {c['end']-c['start']:.2f}초 {len(c['text'])}자 {cps_of(c):.1f} cps  {c['text']}", file=sys.stderr)
    if bad: print(f"ERROR: {CPS_MAX:g} cps 를 넘는 줄 {len(bad)}개 — 읽을 수 없는 속도입니다", file=sys.stderr)
    if rest: print(f"참고: 이번에 안 돌린 씬에 {CPS_MAX:g} cps 초과 {rest}줄이 남아 있습니다(--ids 없이 다시 도세요)")
    if rows:
        sid, i, c = max(rows, key=lambda r: cps_of(r[2]))
        fast = f"가장 빠른 줄 {cps_of(c):.1f} cps ({sid} {i+1}번째, {c['end']-c['start']:.2f}초 {len(c['text'])}자)"
    else:
        fast = "자막 줄 없음"
    line = (f"{len(done)}/{len(sc['scenes'])}씬 · 자막 {len(rows)}줄 · {fast} · "
            f"{CPS_OK:g} cps 초과 {slow}줄 · {MIN_DUR}초 미만 {shrt}줄 · {tail}")
    return bad, line

done = [s["id"] for s in targets]

if a.emph_only:
    if not caps: die(f"자막이 없습니다: {p['caps']}. --emph-only 는 이미 만든 자막에만 씁니다.")
    no_caps = [s["id"] for s in targets if s["id"] not in caps]
    if no_caps:
        die("자막이 아직 없는 씬: " + ", ".join(no_caps) + "\n  --emph-only 없이 먼저 돌리세요.", 3)
    n = 0
    for s in targets:
        sid = s["id"]
        raw = sentences(s["narration"])
        for i, c in enumerate(caps[sid]):
            c["text"] = strip_emphasis(c["text"])
            fl = emph_flags(raw[i]) if i < len(raw) else []
            for j, w in enumerate(c.get("words", [])):
                w.pop("hl", None)
                if j < len(fl) and fl[j]: w["hl"] = True; n += 1
    jdump(caps, p["caps"])
    # 타이밍을 건드리지 않으므로 여기서는 종료코드로 막지 않는다. 수치는 그대로 찍는다.
    _, line = speed_report(caps, done, f"강조 낱말 {n}개 반영 → {p['caps']}")
    print(line)
    sys.exit(0)

def mk_chunk(cur):
    return {"start": round(cur[0]["start"], 2), "end": round(cur[-1]["end"], 2),
            "text": " ".join(x["word"].strip() for x in cur)}

for s in targets:
    sid = s["id"]
    f = ep/s["narration_file"]
    if not f.exists(): die(f"내레이션 파일 없음: {f}")
    _, ws = transcribe(f, words=True)
    # 청크는 사람이 받아쓰기를 확인하는 용도다. 자막 타이밍은 여기서 나오지 않는다.
    chunks, cur, nch = [], [], 0
    for w in ws:
        tok = w["word"].strip(); cur.append(w); nch += len(tok) + 1
        if nch >= 38 or tok.endswith((".", "?", "!")):
            chunks.append(mk_chunk(cur)); cur, nch = [], 0
    if cur: chunks.append(mk_chunk(cur))
    wc[sid] = chunks
    raw_sents = sentences(s["narration"]); sents = [strip_emphasis(x) for x in raw_sents]
    cc = []
    for i, (a0, b0, wl) in enumerate(align(sents, ws, s["narration_dur"])):
        c = {"start": a0, "end": b0, "text": sents[i], "words": wl}
        fl = emph_flags(raw_sents[i]) if i < len(raw_sents) else []
        for j, w in enumerate(c["words"]):
            if j < len(fl) and fl[j]: w["hl"] = True
        cc.append(c)
    caps[sid] = cc
    print(sid, f"{len(cc)}줄", f"최고 {max((cps_of(c) for c in cc), default=0):.1f} cps",
          f"최단 {min((c['end']-c['start'] for c in cc), default=0):.2f}초")

jdump(wc, p["caps_whisper"]); jdump(caps, p["caps"])
bad, line = speed_report(caps, done, f"자막 생성 → {p['caps']}")
print(line)
sys.exit(3 if bad else 0)
