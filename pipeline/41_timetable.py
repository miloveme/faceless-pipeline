#!/usr/bin/env python3
"""시각표를 읽어 보여준다. **아무것도 만들지 않는다** — scenes_v2.json 을 그대로 읽어 찍기만 한다.
40 이 돌 때마다 시각이 바뀌므로 표를 옮겨 적어 두면 바로 낡는다. 필요할 때 여기서 뽑아 쓴다.
사용: 41_timetable.py <EP> [--frames] [--boundaries] [--at "s03 13.5" ...]

`--at` 은 **씬 안 시각 → 절대 프레임**이다. 스틸을 뽑을 때 이 셈을 손으로 하면
40 이 한 번 돌 때마다 앞 씬이 밀려 **모든 번호가 조용히 낡는다** — E01 에서 s02 를 두 번 다시
만드는 사이 스틸 목록이 두 번 낡았다. 씬 안 시각은 안 바뀌므로 **그것으로 주고받고 번호는 여기서 뽑는다.**"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep")
ap.add_argument("--frames", action="store_true", help="프레임 열만 넓게 (렌더·스틸 뽑을 때)")
ap.add_argument("--boundaries", action="store_true", help="경계만 한 줄씩 (이음매를 볼 때)")
ap.add_argument("--at", metavar="\"<씬id> <씬 안 초>\"", action="append",
                help="씬 안 시각을 절대 프레임으로. 여러 번 줄 수 있다 — 예: --at \"s03 13.5\"")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
if not p["scenes_v2"].exists(): die("scenes_v2.json 이 없습니다 — 먼저 40_nar_finalize.py 를 돌리세요.")
sc = jload(p["scenes_v2"]); L = sc["lead"]
blocks = sc.get("blocks", [])
seg = sorted([(s["t_start"], s["t_end"], s["id"]) for s in sc["scenes"]]
             + [(b["t"], round(b["t"] + b["sec"], 3), b.get("clip", "(빈 화면)")) for b in blocks])
if a.at:
    ID = {s["id"]: s for s in sc["scenes"]}
    BLK = {b.get("clip", f'빈화면@{b["t"]:.3f}'): b for b in blocks}
    print(f"{'자리':16s} {'씬 안':>7s} {'절대 초':>9s} {'프레임':>7s}   ffmpeg -ss")
    bad = 0
    for spec in a.at:
        try:
            sid, off = spec.split(); off = float(off)
        except ValueError:
            die(f'--at 은 "<씬id> <씬 안 초>" 꼴입니다 — 받은 것: {spec!r}', 2)
        if sid in ID:
            t0, t1, what = ID[sid]["t_start"], ID[sid]["t_end"], "씬"
        elif sid in BLK:
            t0, t1, what = BLK[sid]["t"], round(BLK[sid]["t"] + BLK[sid]["sec"], 3), "구간"
        else:
            die(f"{sid} 을 못 찾았습니다 — 씬 {len(ID)}개와 구간 {len(BLK)}개 중에 없습니다\n"
                f"  씬: {' '.join(ID)}\n  구간: {' '.join(BLK)}", 2)
        k = round(t0 * FPS) + round(off * FPS)
        t = k / FPS
        over = "" if t < t1 else f"  ← **{what} 끝({t1:.3f}초)을 넘습니다**"
        if over: bad += 1
        # ffmpeg 의 -ss 는 **그 시각 이후 첫 프레임**을 준다. 반 프레임 앞을 짚어야 그 프레임이 나온다.
        print(f"{sid:16s} {off:7.2f} {t:9.3f} {k:7}   -ss {max(0, k - 0.5) / FPS:.4f}{over}")
    print(f"\n{len(a.at)}자리 · 편 끝 {seg[-1][1]:.3f}초 / {round(seg[-1][1]*FPS)}프레임"
          + (f" · **씬 밖으로 나간 것 {bad}자리**" if bad else " · 다 씬 안입니다"))
    if bad:
        sys.exit(3)
elif a.boundaries:
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
