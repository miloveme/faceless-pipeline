#!/usr/bin/env python3
"""마스터의 **완전 무음**이 시각표가 말하는 자리·길이와 맞는가. `60_render_master.sh` 가 부른다.

씬과 씬 사이에는 무음이 **있어야 한다** — 앞 씬의 말이 끝나고 남은 자리 + 다음 씬의 `LEAD`.
그래서 「무음이 있다」로는 아무것도 못 가린다. **얼마나 있어야 하는지를 시각표에서 셈해서 댄다.**

**왜 필요한가** — v10 마스터에서 s07 의 내레이션 **마지막 1.84초가 통째로 빠졌다.**
파일도 시각표도 멀쩡했고(그 구간만 다시 그리면 소리가 나온다), **긴 렌더에서 한 번 흘린 것**이다.
`silencedetect` 로는 안 보였다 — 다른 자리와 같은 「무음」이고 **길이만 1.9초 길었다.**
33곳이 1.30~1.41 인데 한 곳이 3.22 였다. **분모가 있어야 보이는 종류다.**

사용: _silence_check.py <마스터.mp4> <EP>
종료코드: 0 통과 · 2 설정 오류 · 3 검사 실패
"""
import json
import pathlib
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ep_dir  # noqa: E402

SR = 8000
MARGIN = 0.30          # 이만큼 넘게 길면 잡는다. h264/aac 경계에서 ±0.1 은 늘 흔들린다


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


if len(sys.argv) < 3:
    die("사용: _silence_check.py <마스터.mp4> <EP>")
master = pathlib.Path(sys.argv[1])
if not master.exists():
    die(f"마스터가 없습니다: {master}")
ep = ep_dir(sys.argv[2])
p = ep / "script" / "scenes_v2.json"
if not p.exists():
    die(f"scenes_v2.json 이 없습니다: {p}")
sc = json.loads(p.read_text(encoding="utf-8"))
LEAD = sc["lead"]
SCN = sc["scenes"]

# **같은 판인가 먼저 본다.** 시각표가 바뀐 뒤 옛 마스터에 대면 서른 곳이 다 어긋나게 나온다 —
# 그러면 「검사가 잡았다」가 아니라 **「엉뚱한 것을 쟀다」**다. 길이로 가른다.
_o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(master)], capture_output=True, text=True).stdout.strip()
_mdur = float(_o) if _o else 0.0
_want_dur = max([x["t_end"] for x in sc["scenes"]]
                + [b["t"] + b["sec"] for b in sc.get("blocks", [])] + [0])
if abs(_mdur - _want_dur) > 0.5:
    die(f"마스터와 시각표가 다른 판입니다 — 마스터 {_mdur:.3f}초 · 시각표 {_want_dur:.3f}초\n"
        f"  ({master})\n"
        f"  이 검사는 **그 시각표로 구운 마스터**에만 뜻이 있습니다.", 2)

# ── 있어야 할 무음: 앞 씬의 말이 끝난 뒤부터 다음 씬의 말이 시작할 때까지
want = []
for i, s in enumerate(SCN):
    end = s["t_start"] + LEAD + s["narration_dur"]
    nxt = SCN[i + 1]["t_start"] + LEAD if i + 1 < len(SCN) else s["t_end"]
    if nxt - end > 0.05:
        want.append((round(end, 3), round(nxt - end, 3), s["id"]))

# ── 실제 무음: **값이 정확히 0** 인 구간. 「조용하다」가 아니라 「없다」를 센다
tmp = master.with_suffix(".silence.wav")
subprocess.run(["ffmpeg", "-v", "error", "-i", str(master), "-vn", "-ar", str(SR), "-ac", "1",
                "-f", "wav", str(tmp), "-y"], check=True)
with wave.open(str(tmp)) as w:
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
tmp.unlink(missing_ok=True)
z = a == 0
got, start = [], None
for i, v in enumerate(z):
    if v and start is None:
        start = i
    if not v and start is not None:
        if i - start >= SR * 0.25:
            got.append((start / SR, (i - start) / SR))
        start = None
if start is not None and (len(z) - start) >= SR * 0.25:
    got.append((start / SR, (len(z) - start) / SR))

print(f"무음 검사: 시각표가 말하는 자리 **{len(want)}곳** · 마스터에서 잰 것 **{len(got)}곳** "
      f"(0.25초 넘는 **완전 무음** · 8kHz 로 재어서 봄)")

# **겹치는가로 짝을 짓는다.** 시작 시각으로 재면 안 된다 — 말이 일찍 끊기면 무음이 **앞으로**
# 자라서 시작이 1.8초 밀린다. 그러면 「길다」가 아니라 「없다」로 잘못 나온다(실제로 그랬다).
def overlap(g, t, d):
    return min(g[0] + g[1], t + d) - max(g[0], t) > 0


bad, used = [], set()
for t, d, sid in want:
    near = [g for g in got if overlap(g, t, d)]
    if not near:
        bad.append((sid, t, d, None, None))
        continue
    g = max(near, key=lambda x: x[1])
    used.add(g)
    if g[1] > d + MARGIN:
        bad.append((sid, t, d, g[1], t - g[0]))

# 씬 밖 구간의 경계와 인트로의 빈 화면은 시각표의 「씬 사이」가 아니다 —
# 1초 아래는 그 언저리라 안 센다. **몇 개를 빼는지는 찍는다.**
extra = [g for g in got if g not in used and g[1] >= 1.0]
_edge = [g for g in got if g not in used and g[1] < 1.0]
ds = [d for _, d in got]
if ds:
    print(f"  잰 무음 — 중앙 {np.median(ds):.3f}초 · 최대 {max(ds):.3f}초 · 합 {sum(ds):.2f}초")
if _edge:
    print(f"  씬 밖 구간 언저리의 1초 미만 무음 **{len(_edge)}곳**은 안 셉니다 "
          + "(" + " · ".join(f"{t:.2f}초 {d:.2f}초" for t, d in _edge) + ")")
if extra:
    print(f"  ← **시각표에 없는 1초 넘는 무음 {len(extra)}곳**: "
          + " · ".join(f"{t:.2f}초부터 {d:.2f}초" for t, d in extra[:5]))

# ── 반대 방향: **씬마다 말이 시각표대로 있는가**(음악 감독이 만들어 대 본 것을 여기 합친다)
# 무음 쪽만 보면 **끝이 잘린 것**은 잡아도 **씬마다 얼마나 맞는지**는 안 나온다.
# 「31/31」처럼 **분모가 붙은 한 줄**이 나오는 것이 이쪽의 값이다.
# 음악 감독 실측 — v10 은 s07 이 **−1.840** 으로 울리고 나머지 30씬은 −0.05 안, v11 은 31/31.
# **결함이 있는 판에 대서 울리는 것을 먼저 봤다. 안 울리면 검사가 아니라 장식이다**(음악 감독).
SPK = 40      # 이보다 큰 표본을 「소리 있음」으로 본다 (16비트에서 -58dBFS 언저리)
TOL = 0.20    # 씬마다 이 안이면 맞은 것. **음악 감독 값**이다
ends = []
for sn in SCN:
    a0 = int(round((sn["t_start"] + LEAD) * SR))
    b0 = int(round((sn["t_start"] + LEAD + sn["narration_dur"]) * SR))
    seg = np.abs(a[a0:min(b0 + int(0.4 * SR), len(a))])
    nz = np.nonzero(seg > SPK)[0]
    if len(nz) == 0:
        ends.append((sn["id"], None, None))
        continue
    ends.append((sn["id"], nz[0] / SR - 0.0, (a0 + nz[-1]) / SR - (b0 / SR)))
off = [(i, s0, e0) for i, s0, e0 in ends if e0 is None or abs(e0) > TOL]
print(f"  말 끝이 시각표와 맞는가 — **{len(SCN) - len(off)}/{len(SCN)}** 씬이 ±{TOL:.2f}초 안 "
      f"(슬롯 안에서 소리가 나는 마지막 자리를 잽니다 · 문턱 {SPK})")
for i, s0, e0 in off:
    if e0 is None:
        print(f"    ← **{i} 슬롯에 소리가 없습니다**")
    else:
        print(f"    ← **{i} 말 끝이 {e0:+.3f}초** — 있어야 할 자리보다 그만큼 이릅니다")
if off:
    bad += [(i, 0, 0, None, None) for i, _, _ in off if not any(b[0] == i for b in bad)]

if bad:
    for sid, t, d, g, early in bad:
        if g is None:
            print(f"  ← **{sid} 뒤에 있어야 할 무음이 없습니다** — {t:.3f}초부터 {d:.3f}초")
        else:
            print(f"  ← **{sid} 뒤 무음이 {g - d:+.2f}초 깁니다** — "
                  f"있어야 할 {d:.3f}초 · 잰 것 **{g:.3f}초**")
            print(f"      말이 {t:.3f}초에 끝나야 하는데 **{early:.2f}초 일찍 끊겼습니다.**")
            print(f"      파일과 시각표가 맞는데 마스터에만 없으면 **렌더가 흘린 것**입니다 — "
                  f"그 구간만 다시 그려서 대 보세요.")
    sys.exit(3)
print(f"  있어야 할 자리 {len(want)}곳이 다 있고 **{MARGIN}초 넘게 긴 것 0곳**입니다")
