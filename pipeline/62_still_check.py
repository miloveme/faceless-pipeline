#!/usr/bin/env python3
"""마스터가 얼마나 정지해 있나. **문법과 무관한 잣대다** — 프레임 사이가 안 바뀌는 시간을 센다.

면적(%)은 그릇이 바뀌면 같이 바뀐다(v5 `panel` 안쪽 1,217,144px² → v8 `sheet` 1,512,480px², +24.3%)
그래서 판이 다르면 못 댄다. **정지 비율은 그릇에 안 걸린다.**

  정지 비율 = (이웃 프레임 차가 임계 아래인 시간) / 편 길이
  이어진 정지 구간이 `--max-still` 초를 넘으면 그 자리를 찍는다

사용: 62_still_check.py <마스터.mp4> [--fps 10] [--th 1.0] [--max-still 3.0] [--report]"""
import argparse, subprocess, sys, numpy as np
from common import die

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
ap.add_argument("--report", action="store_true", help="차이값 분포를 같이 찍는다 — 임계를 정할 때 본다")
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
print(f"정지 비율 **{pct:.1f}%**  ({a.fps}fps 로 {n}장 · 임계 평균 화소 차 {a.th} · 편 {total:.1f}초"
      + f" · 아래 {a.cut_bottom*100:.1f}% 는 빼고 봄 — 자막 띠)")
print(f"  정지 구간 {len(runs)}개 · 가장 긴 것 {max((r[1] for r in runs), default=0):.2f}초")
long = [r for r in runs if r[1] > a.max_still]
if long:
    print(f"  ← **{a.max_still}초를 넘게 안 바뀌는 자리 {len(long)}곳**")
    for t, L in long: print(f"      {t:7.2f}초 부터 {L:.2f}초  (프레임 {round(t*30)})")
else:
    print(f"  {a.max_still}초를 넘게 안 바뀌는 자리 0곳")
if a.report:
    q = np.percentile(d, [1, 5, 10, 25, 50, 75, 90, 99])
    print("  차이값 분포:", " · ".join(f"{p}%={v:.2f}" for p, v in zip([1,5,10,25,50,75,90,99], q)))
    print(f"  0.5 아래 {int((d<0.5).sum())}장 · 1.0 아래 {int((d<1.0).sum())}장 · "
          f"2.0 아래 {int((d<2.0).sum())}장 / 전체 {len(d)}장")
    print("  **두 무리가 갈리는 골짜기에 임계를 두세요** — 정지 화면은 0 에 몰리고 움직이는 것은 멀리 있습니다")
