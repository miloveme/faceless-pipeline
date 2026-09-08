#!/usr/bin/env python3
"""마스터가 얼마나 정지해 있나. **문법과 무관한 잣대다** — 프레임 사이가 안 바뀌는 시간을 센다.

면적(%)은 그릇이 바뀌면 같이 바뀐다(v5 `panel` 안쪽 1,217,144px² → v8 `sheet` 1,512,480px², +24.3%)
그래서 판이 다르면 못 댄다. **정지 비율은 그릇에 안 걸린다.**

  정지 비율 = (이웃 프레임 차가 임계 아래인 시간) / 편 길이
  이어진 정지 구간이 `--max-still` 초를 넘으면 그 자리를 찍는다

**자막 띠를 뺀 값과 안 뺀 값을 나란히 놓지 마라.** 보는 화소가 20% 줄면 같은 움직임이라도
평균 차가 그만큼 커진다. 잣대가 다른 두 수다 — 어느 쪽으로 잰 값인지 적고 비교해라.

**이 값은 가르는 잣대가 아니라 자리를 찾는 잣대다.** 「길게 안 바뀐다」가 곧 「지루하다」는 아니다 —
새로 뜬 것을 읽는 시간일 수도 있다. **가르는 것은 미술·연출이다.**
`--ep` `--stills` 를 주면 그쪽이 가를 수 있는 형태로 낸다 — 씬·씬 안 시각·길이·그때 자막·시작 프레임 스틸.

사용: 62_still_check.py <마스터.mp4> [--fps 10] [--th 0.5] [--max-still 3.0]
                        [--ep E01_… --stills <폴더>]"""
import argparse, subprocess, sys, numpy as np
from common import die, FPS

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--fps", type=float, default=10.0, help="초당 몇 장을 볼까 (기본 10 — 0.9초 정지도 잡힌다)")
# **임계 0.5 는 재서 정했다**(엔지니어). **자막 띠를 뺀 뒤의 값이다** — 아래 참고.
#   정지한 그림      crf18 로 구운 정지 프레임 30장의 차가 **전부 0.00** (h264 가 같은 프레임을 그대로 낸다)
#   자막만 바뀔 때    자막 띠를 빼면 **0.00** (36 표본) — 화면에 안 남는다
#   움직이는 것      실사 클립 1% 분위 **0.94** · 중앙값 3.23
# **자막 띠를 안 빼면 자막만 바뀌는 자리가 최대 1.20 까지 오른다**(그림이 멈춘 구간에서 잰 값).
# 낱말 하나가 회색에서 흰색으로 바뀌는 것이 화면 평균을 그만큼 움직인다 —
# **임계 0.5 를 넘으므로 안 빼면 「말하는 동안은 늘 움직임」이 되어 검사가 아무것도 못 잡는다.**
# (처음에 표본 넷으로 재서 0.05~0.18 로 봤다가 36 표본으로 다시 재니 1.20 이었다. **표본이 적었다.**)
# 1.0 으로 두면 실사 99장 중 4장이 「정지」로 잡힌다. 0.5 는 0.02 와 0.94 사이의 한가운데다.
# **값을 바꾸면 여기 근거도 같이 고쳐라** — 수만 바꾸면 다음 사람이 왜 그 수인지 모른다.
ap.add_argument("--th", type=float, default=0.5,
                help="이웃 프레임 평균 화소 차가 이 아래면 정지 (0~255, 기본 0.5)")
ap.add_argument("--max-still", type=float, default=3.0, help="이 초를 넘게 안 바뀌면 찍는다")
# **자막 띠를 뺀다.** 노래방 강조가 낱말마다 바뀌고 낱말이 0.2~0.5초라, 안 빼면
# **내레이션이 도는 동안 어느 프레임도 「정지」가 아니다.** 그러면 검사가 늘 「0곳」을 내는데
# 그건 화면이 움직여서가 아니라 자막이 움직여서다(연출이 잡았다).
# 목표값 「3초 넘게 아무것도 안 바뀌는 자리가 없다」는 **그림 층**의 이야기다 — 자막은 어차피 바뀐다.
# 기본 0.2019 = grammars.json 의 safeBottom 218 ÷ 1080. **문법이 다르면 그 값으로 바꾼다.**
ap.add_argument("--cut-bottom", type=float, default=218 / 1080,
                help="아래 이 비율만큼 빼고 잰다 (기본 218/1080 = 자막 안전영역)")
# **검정 구간은 따로 훑는다.** 정지 훑기는 자막 띠를 빼고 보는데, 검정은 **화면 전부가** 검어야
# 검정이라 자막이 떠 있으면 검정이 아니다. 같은 배열을 나눠 쓰면 「그림은 검고 자막은 떠 있는」
# 프레임이 검정으로 잡힌다. 임계 5 는 미술이 준 값이다 — h264 가 #000 을 정확히 0 으로 내지 않는다.
ap.add_argument("--dark", type=float, metavar="밝기", nargs="?", const=5.0,
                help="화면 전부의 밝기 평균이 이 아래인 구간도 찾는다 (기본 5 · 0~255)")
# **안전영역 안에서 자막이 절대 안 쓰는 띠**에 씬 요소가 들어왔나.
# 「아래 218px 이 바탕색이 아닌 프레임」을 그냥 세면 **자막이 늘 걸린다** — 자막이 거기 있는 게 정상이다.
# 그래서 자막 상자 **위쪽** 띠만 본다. E01 실측으로 자막 상자가 y937 부터라 862~930 을 본다.
# **낱말로 세는 것(`<Bleed>` · `inset: 0`)을 화소로 대는 검사다**(미술) — 다른 꼴로 화면을 채우는
# 자리가 있어도 여기서는 잡힌다. 자막 상자 자리가 바뀌면 이 값도 바꿔야 한다.
ap.add_argument("--safe-band", nargs="?", const="862:930", metavar="위:아래",
                help="안전영역 중 자막이 안 쓰는 띠에 씬 요소가 있나 (기본 862:930)")
ap.add_argument("--bg", type=int, default=17, help="바탕색 회색값 (기본 17 = #0f1115)")
ap.add_argument("--report", action="store_true", help="차이값 분포를 같이 찍는다 — 임계를 정할 때 본다")
ap.add_argument("--ep", help="에피소드. 주면 정지 자리를 **씬·씬 안 시각·그때 자막**으로 풀어 준다")
ap.add_argument("--stills", help="정지가 시작하는 프레임을 이 폴더에 뽑는다 (마스터에서 바로 뜬다)")
# 임계를 낮추면(0.8) 박자 사이가 다 걸려 목록이 길어진다. 그때는 **씬마다 가장 긴 것 하나**만 본다(연출).
ap.add_argument("--per-scene", action="store_true", help="씬마다 가장 긴 정지 하나씩만 찍는다 (--ep 필요)")
# **목록에 안 걸리는 자리도 봐야 할 때가 있다.** 인트로 사이 검은 0.4초가 그렇다 —
# 짧아서 어느 임계에도 안 걸리는데, 원본과 클론을 가르는 자리라 미술이 봐야 한다.
ap.add_argument("--extra-still", type=float, action="append", metavar="초", default=[],
                help="목록과 별개로 이 시각의 스틸도 뽑는다 (여러 번 줄 수 있다 · --stills 필요)")
# **경계 한 프레임을 볼 때는 초로 주지 마라.** 초로 주면 어느 프레임이 나오는지 반올림이 정한다 —
# 9.592 는 f287 도 f288 도 될 수 있다. 프레임 번호로 받아 그 칸 한가운데를 뜬다(미술).
ap.add_argument("--extra-frame", type=int, action="append", metavar="프레임", default=[],
                help="목록과 별개로 이 프레임의 스틸도 뽑는다 (--stills 필요)")
a = ap.parse_args()

W, H = 160, 90                      # 정지 판정에 해상도는 필요 없다. 작게 봐야 인코더 잡음이 씻긴다
keep = max(0.05, 1 - a.cut_bottom)
cmd = ["ffmpeg", "-v", "error", "-i", a.video,
       "-vf", f"fps={a.fps},crop=iw:ih*{keep:.6f}:0:0,scale={W}:{H},format=gray",
       "-f", "rawvideo", "-"]
p = subprocess.run(cmd, capture_output=True)
if p.returncode != 0: die(f"ffmpeg 실패: {p.stderr.decode()[:300]}", 1)
buf = np.frombuffer(p.stdout, dtype=np.uint8)
n = buf.size // (W * H)
if n < 2: die(f"프레임이 {n}장뿐입니다 — 파일을 확인하세요: {a.video}", 1)
fr = buf[: n * W * H].reshape(n, H, W).astype(np.int16)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))      # 이웃 프레임 평균 화소 차
dt = 1.0 / a.fps
still = d < a.th

# 이어진 정지 구간
runs, i = [], 0
while i < len(still):
    if still[i]:
        j = i
        while j < len(still) and still[j]: j += 1
        runs.append((i * dt, (j - i) * dt)); i = j
    else: i += 1

total = n * dt
pct = still.sum() * dt / total * 100

# **씬·자막을 붙인다.** 숫자만으로는 못 가른다(미술) — 「그 순간 화면에 새로 읽을 것이 있었나」를 봐야 하고
# 「자막은 새 얘기로 넘어갔는데 그림이 앞 얘기에 서 있나」도 봐야 한다. **가르는 것은 미술·연출이다.**
SC = CAP = LEAD = BLK = None
if a.ep:
    from common import ep_dir, P, jload
    _p = P(ep_dir(a.ep)); _j = jload(_p["scenes_v2"])
    SC, CAP, LEAD, BLK = _j["scenes"], jload(_p["caps"]), _j["lead"], _j.get("blocks", [])
elif a.per_scene:
    die("--per-scene 은 --ep 가 있어야 합니다 (씬 경계를 알아야 씬마다 셉니다)", 2)

def at(t):
    """그 시각이 어느 씬 안인가 → (씬 id, 씬 안 시각, 그때 자막). 씬 밖이면 (None, None, "")"""
    for x in SC:
        if x["t_start"] <= t < x["t_end"]:
            off = t - x["t_start"]
            for c in CAP.get(x["id"], []):
                if c["start"] + LEAD <= off < c["end"] + LEAD: return x["id"], off, c["text"]
            return x["id"], off, ""
    return None, None, ""

# **두 값에 다 이름을 붙인다.** 차이가 1%p 도 안 나서 판단은 안 갈리는데,
# 값이 안 갈리면 아무도 「무엇을 재고 있나」를 안 묻는다. 그래서 더 이름이 정확해야 한다(연출).
#   편 전체 — 관객이 보는 시간. 참고로만 둔다
#   씬 안   — **판정은 이 값으로 한다**(연출·미술이 같이 정했다). 씬 밖은 클립을 그대로 트는 자리라
#             설계가 없고 언제나 통과한다 — 분모에 넣으면 22초가 공짜로 「움직임」이 되어 값만 좋아진다.
#             면적 11.6% 를 다음 판과 못 대기로 한 것과 같은 자리다: 나아진 것이 아니라 그릇을 재게 된다.
print(f"정지 비율(편 전체) {pct:.1f}%  (참고 — 관객이 본 전부. {a.fps}fps 로 {n}장 · 임계 평균 화소 차 {a.th} · 편 {total:.1f}초"
      + f" · 아래 {a.cut_bottom*100:.1f}% 는 빼고 봄 — 자막 띠)")
if SC:
    # **인트로·꼬리를 뺀 값**(미술 요청). 로고와 끝 카드는 서 있는 것이 설계라
    # 그것까지 세면 「화면이 안 움직인다」가 실제보다 나빠 보인다. **판정은 씬 안 값으로 한다.**
    # **경계는 반올림이다.** ceil/floor 로 자르면 씬마다 양끝에서 최대 한 장씩 빠져
    # 29씬이면 2.8초가 조용히 「씬 밖」으로 샌다. 처음에 그렇게 짰다가 24.9 vs 22.1 로 어긋났다.
    ins = np.zeros(len(still), bool)
    for x in SC:
        ins[max(0, round(x["t_start"] / dt)):min(len(still), round(x["t_end"] / dt))] = True
    if ins.sum():
        # **뺀 것의 이름은 데이터에서 읽는다.** 처음에 「씬 사이 틈」이라 불렀는데
        # 그 자리에 `tail_m3` 클립이 들어 있었다 — 틈이 아니라 클립이다(연출이 잡았다).
        # 이름을 코드에 박으면 씬 배치가 바뀔 때 조용히 틀린 이름이 남는다. blocks[] 가 이미 안다.
        names, rest = [], (len(still) - ins.sum()) * dt
        for b in BLK:
            i0, i1 = round(b["t"] / dt), round((b["t"] + b["sec"]) / dt)
            sec = (~ins[max(0, i0):min(len(still), i1)]).sum() * dt
            if sec >= dt: names.append(f'{b.get("clip") or "전환"} {sec:.1f}'); rest -= sec
        if rest >= dt: names.append(f"이름 없는 구간 {rest:.1f}")
        print(f"정지 비율(씬 안)   **{still[ins].sum()/ins.sum()*100:.1f}%**  ← 판정은 이 값  "
              f"(씬 안 {ins.sum()*dt:.1f}초 · 뺀 것 {(len(still)-ins.sum())*dt:.1f}초 = "
              + " + ".join(names) + " · 전부 씬 밖 클립)")
print(f"  정지 구간 {len(runs)}개 · 가장 긴 것 {max((r[1] for r in runs), default=0):.2f}초")

long = [r for r in runs if r[1] > a.max_still]
if a.per_scene:
    best = {}
    for t, L in long:
        sid = at(t)[0]
        if sid and L > best.get(sid, (0, 0))[1]: best[sid] = (t, L)
    order = {x["id"]: k for k, x in enumerate(SC)}
    shown = sorted(best.values(), key=lambda r: order[at(r[0])[0]])
    print(f"  ← {a.max_still}초를 넘는 자리 {len(long)}곳 중 **씬마다 가장 긴 것 {len(shown)}줄**"
          f" (씬 {len(SC)}개 중 {len(shown)}개에 있음 · 씬 밖은 안 셈)")
    # **정지 목록의 구멍을 메우는 칸**(미술). 낱말 하나가 커지는 것이 화면 평균 차 0.5 근처라
    # **작은 것 하나가 계속 움직이면 그 씬은 목록에서 빠진다** — 보기에는 멈춰 있는데도.
    # 그 자리를 「차가 0.5~1.5 인 표본의 비율」로 낸다. 실사는 그 위에 있다(1% 분위 0.81 · 중앙 2.70).
    # **새 훑기가 아니다** — 이미 잰 `d` 에 조건 하나다. 비율이 높은 씬이 미술이 열어 볼 씬이다.
    # **1초 창.** 이웃 프레임 차(1/30초)는 두 가지를 못 본다 —
    #   페이드   0.4초짜리가 10fps 에서 넉 조각이 되어 조각마다 임계 아래로 간다.
    #            s01 은 「20.40초 정지」인데 첫 장과 마지막 장의 차가 1.316 이다
    #   작은 창  칸 둘이 화면의 26% 면 실사 중앙 2.70 × 0.26 = 0.70 이라 「작은 움직임」으로 잡힌다
    # **1초 떨어진 두 장을 대면 둘 다 갈린다**(미술). 열 칸 떨어진 표본이 1초다.
    _d1 = np.abs(fr[:-int(a.fps)].astype(np.int16) - fr[int(a.fps):]).mean(axis=(1, 2)) \
          if len(fr) > int(a.fps) else np.zeros(0)
    # 밴드 칸은 남긴다 — **「작은 창에서 실사가 돈다」를 재는 값**으로는 맞다(미술). 이름만 그것이다.
    # **들어오는 전환은 뺀다.** 씬 첫 0.2~0.5초는 씬 층이 통째로 밀려 들어오는 구간이라
    # 1초 창이 그것을 「이 씬이 바뀐다」로 잡는다 — s01 이 최대 0.44 대신 40.78 로 나왔다.
    # 전환 길이는 **앞에 오는 것**이 갖는다(scenes_v2 의 transition). 씬·구간을 시각으로 세운다.
    _tr = (jload(_p["scenes_v2"]).get("transition") or {"default": 0.0, "after": {}})
    _ord = sorted([(x["t_start"], x["id"]) for x in SC]
                  + [(b["t"], b.get("clip") or f'빈화면@{b["t"]:.3f}') for b in BLK])
    _enter = {}
    for _k, (_t, _id) in enumerate(_ord):
        _prev = _ord[_k - 1][1] if _k > 0 else None
        _enter[_id] = _tr["after"].get(_prev, _tr["default"]) if _prev else 0.0
    _lo, _hi = a.th, a.th * 3
    print(f"  씬별  **1초차** = 1초 떨어진 두 장의 차 (페이드·작은 창을 다 본다)"
          f"  ·  작은창실사 = 이웃 프레임 차가 {_lo}~{_hi} 인 표본의 비율")
    for x in SC:
        i0, i1 = max(0, round(x["t_start"] / dt)), min(len(d), round(x["t_end"] / dt))
        seg = d[i0:i1]
        if not len(seg): continue
        _sm = float(((seg >= _lo) & (seg < _hi)).mean() * 100)
        _lg = max((L for t, L in runs if at(t)[0] == x["id"]), default=0.0)
        # **두 끝이 다 그 씬 안**인 표본만 쓴다. 안 그러면 마지막 초가 다음 씬과 비교되어
        # 「이 씬이 얼마나 안 바뀌나」에 전환이 섞인다 — s01 최대가 0.44 대신 40.78 로 나왔다.
        # 두 끝이 다 그 씬 안이고, **들어오는 전환이 끝난 뒤**인 표본만 쓴다.
        _j0 = i0 + round(_enter.get(x["id"], 0.0) / dt)
        _s1 = _d1[_j0:max(_j0, min(len(_d1), i1 - int(a.fps)))]
        _c = (f"1초차 중앙 {np.median(_s1):6.2f} · 최대 {_s1.max():6.2f} · 0.5아래 {float((_s1 < a.th).mean()*100):3.0f}%"
              if len(_s1) else "1초차 —")
        print(f"      {x['id']}  정지 {_lg:5.2f}초 · {_c} · 작은창실사 {_sm:3.0f}%"
              + ("  ←" if _lg > a.max_still else ""))
else:
    shown = long
    print(f"  ← **{a.max_still}초를 넘게 안 바뀌는 자리 {len(shown)}곳**" if shown
          else f"  {a.max_still}초를 넘게 안 바뀌는 자리 0곳")

if a.stills and shown:
    import pathlib as _pl; _pl.Path(a.stills).mkdir(parents=True, exist_ok=True)
for t, L in shown:
    fnum = round(t * FPS)
    line = f"      {t:7.2f}초 부터 {L:.2f}초  (프레임 {fnum})"
    if SC:
        sid, off, said = at(t)
        line += (f"\n         {sid} 안 {off:.2f}초" + (f'  자막: 「{said}」' if said else "  자막: (없음)")
                 if sid else "\n         씬 밖 구간 — 인트로·꼬리는 서 있는 것이 설계다")
    print(line)
    if a.stills:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", a.video,
                        "-frames:v", "1", f"{a.stills}/still_{fnum}.png"], check=False)
if a.stills and shown: print(f"      스틸 {len(shown)}장 → {a.stills}/  (**정지가 시작하는 프레임**)")

if a.extra_still or a.extra_frame:
    if not a.stills: die("--extra-still / --extra-frame 은 --stills 가 있어야 합니다 (뽑을 곳이 없습니다)", 2)
    import pathlib as _pl; _pl.Path(a.stills).mkdir(parents=True, exist_ok=True)
    # **둘 다 프레임 번호로 바꿔서 뽑는다.** 초로 뽑으면 어느 칸이 나오는지 반올림이 정한다.
    # 그리고 `-ss` 는 **그 시각 이후 첫 프레임**을 낸다 — 칸 한가운데를 주면 다음 칸이 나온다.
    # (합성 클립으로 확인했다: f17 을 0.5833 로 주니 f18 이 나왔다.) **반 칸 앞**을 준다.
    want = [(round(t * FPS), f"at_{round(t * FPS)}") for t in a.extra_still] \
         + [(k, f"f{k}") for k in a.extra_frame]
    print(f"  따로 뽑은 자리 {len(want)}장 (목록과 무관 — 요청받은 자리)")
    for k, name in want:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, k - 0.5) / FPS:.4f}",
                        "-i", a.video, "-frames:v", "1", f"{a.stills}/{name}.png"], check=False)
        t = k / FPS
        where = f"{at(t)[0]} 안 {at(t)[1]:.2f}초" if SC and at(t)[0] else "씬 밖"
        print(f"      프레임 {k:5d} ({t:7.3f}초)  {where}  → {name}.png")

if a.dark is not None:
    p2 = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video,
                         "-vf", f"fps={a.fps},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                        capture_output=True)
    if p2.returncode != 0: die(f"ffmpeg 실패(검정 훑기): {p2.stderr.decode()[:300]}", 1)
    b2 = np.frombuffer(p2.stdout, dtype=np.uint8)
    n2 = b2.size // (W * H)
    m = b2[: n2 * W * H].reshape(n2, H, W).mean(axis=(1, 2))      # **자르지 않은 전 화면** 밝기
    dark, dr, i = m < a.dark, [], 0
    while i < n2:
        if dark[i]:
            j = i
            while j < n2 and dark[j]: j += 1
            dr.append((i * dt, (j - i) * dt)); i = j
        else: i += 1
    print(f"  검정 구간 **{len(dr)}곳** (전 화면 밝기 평균 {a.dark} 아래 · 자막 띠도 포함해서 봄)"
          + (f" · 합 {sum(x[1] for x in dr):.2f}초" if dr else " — 편에 검정이 없습니다"))
    # **평균만으로는 「고른 검정」과 「어두운 무늬」가 안 갈린다.** 화소 최대까지 같이 낸다 —
    # 최대도 0 에 가까우면 전 화면이 같은 값이고, 크면 어딘가에 띠나 무늬가 남아 있다.
    _b2 = b2[: n2 * W * H].reshape(n2, H, W)
    for t, L in dr:
        i0, i1 = round(t / dt), round((t + L) / dt)
        w = ""
        if SC:
            sid, off, _ = at(t)
            w = f"  {sid} 안 {off:.2f}초" if sid else "  씬 밖 구간"
        print(f"      {t:7.2f}초 부터 {L:.2f}초  (프레임 {round(t * FPS)} · 평균 {m[i0:i1].min():.1f}~{m[i0:i1].max():.1f}"
              f" · 가장 밝은 화소 {int(_b2[i0:i1].max())}){w}")

if a.safe_band is not None:
    _t0, _b0 = (int(x) for x in a.safe_band.split(":"))
    _hh = _b0 - _t0
    if _hh <= 0: die(f"--safe-band 는 「위:아래」이고 아래가 커야 합니다 — 받은 값 {a.safe_band}", 2)
    # 씬 요소는 한 화소만 들어와도 들어온 것이다. 그래서 **줄이지 않고 가로만 줄인다** —
    # 세로를 줄이면 띠 안 얇은 선이 이웃 줄과 섞여 사라진다.
    _P = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video,
                         "-vf", f"crop=1920:{_hh}:0:{_t0},scale=480:{_hh},format=gray",
                         "-f", "rawvideo", "-"], capture_output=True)
    if _P.returncode != 0: die(f"ffmpeg 실패(안전영역 띠): {_P.stderr.decode()[:300]}", 1)
    _b = np.frombuffer(_P.stdout, dtype=np.uint8)
    _n = _b.size // (480 * _hh)
    _fr = _b[: _n * 480 * _hh].reshape(_n, _hh, 480)
    _th = a.bg + 13                      # h264 가 평평한 바탕도 ±10 쯤 흔든다. 그 위로 잡는다
    _hit = (_fr > _th).reshape(_n, -1).sum(axis=1)
    _idx = np.nonzero(_hit)[0]
    print(f"안전영역 띠 검사: y{_t0}~{_b0} · {_n}프레임 중 **바탕 아닌 것 {len(_idx)}프레임**"
          f" (임계 {_th} · 바탕 {a.bg})")
    if len(_idx):
        _by = {}
        for i in _idx:
            _k = at(i / FPS)[0] if SC else None
            _by[_k or "씬 밖"] = _by.get(_k or "씬 밖", 0) + 1
        for _k, _v in sorted(_by.items(), key=lambda x: -x[1]):
            print(f"      {_k} {_v}프레임 ({_v/FPS:.2f}초)")
    else:
        print("      **0곳** — 자막 위 띠에 씬 요소가 한 프레임도 안 들어옵니다")

if a.report:
    q = np.percentile(d, [1, 5, 10, 25, 50, 75, 90, 99])
    print("  차이값 분포:", " · ".join(f"{p}%={v:.2f}" for p, v in zip([1,5,10,25,50,75,90,99], q)))
    print(f"  0.5 아래 {int((d<0.5).sum())}장 · 1.0 아래 {int((d<1.0).sum())}장 · "
          f"2.0 아래 {int((d<2.0).sum())}장 / 전체 {len(d)}장")
    print("  **두 무리가 갈리는 골짜기에 임계를 두세요** — 정지 화면은 0 에 몰리고 움직이는 것은 멀리 있습니다")
