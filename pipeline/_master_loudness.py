#!/usr/bin/env python3
"""마스터의 음량과 클리핑을 잰다. 60 이 굽고 나서 부른다.

60 은 이 수를 **찍기만** 했다 — `awk` 로 0.5 LU 를 넘으면 한 줄 띄우고 그대로 지나갔다.
늘 켜진 경고는 세 번째부터 안 읽힌다. 그리고 **클리핑은 아예 안 봤다.**

**무엇으로 가르나**
  음량   |I − MASTER_LUFS| > MASTER_LUFS_TOL 이면 실패.
         두 패스 linear 가 TP 한계에 걸려 게인을 못 올리면 조용히 -15.2 로 나가는데,
         유튜브 정규화가 그걸 다시 올리면서 **음악 감독이 맞춰 놓은 구간 관계가 흔들린다.**
  클리핑  풀스케일(|x| >= 1.0) 이상 샘플이 하나라도 있으면 실패.

**트루피크로는 안 가른다.** `MASTER_TP`(-1.5)는 loudnorm 에 넣는 **목표선**이지 판정선이 아니다.
ebur128 의 Peak 은 dBFS 한 자리로 반올림돼 실측이 -1.5 와 -1.4 로 갈린다 —
E01 마스터 일곱 장이 **-1.5 다섯 · -1.4 둘**이다. 여기에 문턱을 두면 멀쩡한 둘이 걸린다.
같은 판단이 씬 단위에 이미 있다(`common.py` 의 `NAR_TP_MAX` 주석, 음악 감독).
그래서 피크는 **찍기만** 한다.

임계값은 전부 `common.py` 에 있다. 여기서 수를 정하지 않는다.

종료코드: 0 통과 · 1 파일 문제 · 3 음량이나 클리핑이 걸림
사용: _master_loudness.py <마스터.mp4>
"""
import argparse, pathlib, sys
from common import MASTER_LUFS, MASTER_LUFS_TOL, MASTER_TP, clipped, lufs

ap = argparse.ArgumentParser()
ap.add_argument("master")
a = ap.parse_args()

m = pathlib.Path(a.master)
if not m.exists():
    print(f"ERROR: 마스터가 없습니다: {m}", file=sys.stderr); sys.exit(1)

I, pk = lufs(m)
if I is None:
    print(f"ERROR: 음량을 못 읽었습니다 (소리 트랙이 없나요?): {m}", file=sys.stderr); sys.exit(1)
n_clip = clipped(m)
d = abs(I - MASTER_LUFS)

print(f"마스터 음량: I {I} LUFS (목표 {MASTER_LUFS} · 차 {d:.2f} LU · 허용 {MASTER_LUFS_TOL}) · "
      f"피크 {pk} dBFS (목표선 {MASTER_TP} — 판정 안 함) · 풀스케일 이상 샘플 {n_clip}개")

bad = []
if d > MASTER_LUFS_TOL:
    bad.append(f"음량이 목표 {MASTER_LUFS} 에서 {d:.2f} LU 벗어났습니다 (허용 {MASTER_LUFS_TOL}).\n"
               f"    두 패스 linear 가 TP 한계에 걸려 게인을 낮춘 것입니다. 음악 감독에게 알리세요 —\n"
               f"    이대로 나가면 유튜브 정규화가 다시 올리면서 맞춰 놓은 구간 관계가 흔들립니다.")
if n_clip:
    bad.append(f"클리핑입니다 — 풀스케일 이상 샘플 {n_clip}개.\n"
               f"    피크 표시({pk} dBFS)는 반올림이라 이걸 못 가립니다. 샘플 수로 봅니다.")
if bad:
    print(f"마스터 음량 검사 실패 — {len(bad)}건", file=sys.stderr)
    for b in bad: print(f"  · {b}", file=sys.stderr)
    sys.exit(3)
