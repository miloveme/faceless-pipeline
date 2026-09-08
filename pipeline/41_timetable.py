#!/usr/bin/env python3
"""시각표를 읽어 보여준다. **아무것도 만들지 않는다** — scenes_v2.json 을 그대로 읽어 찍기만 한다.
40 이 돌 때마다 시각이 바뀌므로 표를 옮겨 적어 두면 바로 낡는다. 필요할 때 여기서 뽑아 쓴다.
사용: 41_timetable.py <EP> [--frames] [--boundaries]"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep")
ap.add_argument("--frames", action="store_true", help="프레임 열만 넓게 (렌더·스틸 뽑을 때)")
ap.add_argument("--boundaries", action="store_true", help="경계만 한 줄씩 (이음매를 볼 때)")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
if not p["scenes_v2"].exists(): die("scenes_v2.json 이 없습니다 — 먼저 40_nar_finalize.py 를 돌리세요.")
sc = jload(p["scenes_v2"]); L = sc["lead"]
blocks = sc.get("blocks", [])
seg = sorted([(s["t_start"], s["t_end"], s["id"]) for s in sc["scenes"]]
             + [(b["t"], round(b["t"] + b["sec"], 3), b.get("clip", "(빈 화면)")) for b in blocks])
if a.boundaries:
    print(f"{'초':>9} {'프레임':>7}  앞 → 뒤")
    prev = None
    for x0, _, name in seg:
        print(f"{x0:9.3f} {round(x0*FPS):7}  {prev or '(편 시작)'} → {name}"); prev = name
    print(f"{seg[-1][1]:9.3f} {round(seg[-1][1]*FPS):7}  {prev} → (편 끝)")
else:
    print(f"씬     슬롯 구간(초)      프레임@{FPS}    슬롯    말 구간(초)   (말 = t_start+LEAD 부터 내레이션 길이만큼)")
    for s in sc["scenes"]:
        t0, t1 = s["t_start"], s["t_end"]
        print(f'{s["id"]}  {t0:7.2f}~{t1:7.2f}  {round(t0*FPS):5}~{round(t1*FPS):5}  {t1-t0:5.2f}  '
              f'{t0+L:7.2f}~{t0+L+s["narration_dur"]:7.2f}' + (f'  min_sec {s["min_sec"]}' if s.get("min_sec") else ""))
    if blocks:
        print("씬 밖 구간: " + " · ".join(
            f'{b.get("clip","(빈 화면)")} {b["t"]:.3f}~{round(b["t"]+b["sec"],3):.3f} '
            f'({round(b["t"]*FPS)}~{round((b["t"]+b["sec"])*FPS)}f)' for b in blocks))
_bad = sum(1 for x, y in zip(seg, seg[1:]) if round(x[1]*FPS) != round(y[0]*FPS))
print(f"\n편 끝 {seg[-1][1]:.3f}초 / {round(seg[-1][1]*FPS)}프레임 · 씬 {len(sc['scenes'])}개 + 구간 {len(blocks)}개 "
      f"· 경계 {len(seg)-1}곳 · 프레임에서 어긋난 곳 {_bad}곳"
      + (f" · target_duration_sec {sc['target_duration_sec']}" if "target_duration_sec" in sc else ""))
if _bad: die("경계가 프레임에서 어긋납니다 — 55_remotion_sync.py 가 자세히 알려 줍니다.", 3)
