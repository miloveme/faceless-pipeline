#!/usr/bin/env python3
"""화이트보드 애니메이션을 넣을 구간만 잘라 별도 SRT를 만든다(0초 기준으로 재정렬).
srt-whiteboard-animation 스킬은 SRT 전체를 30초 장면으로 쪼개므로, 삽입할 구간만 따로 줘야 한다.
출력 SRT의 총 길이 = 해당 씬들의 t_start~t_end 합 → 렌더된 mp4가 그 자리에 정확히 들어간다.

사용: 80_whiteboard_srt.py <EP> --ids s06,s07,s08 [--out edit/wb_s06_s08.srt]
"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", required=True); ap.add_argument("--out", default="")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
ids = a.ids.split(","); sc = {s["id"]: s for s in jload(p["scenes_v2"])["scenes"]}
caps = jload(p["caps"])
for i in ids:
    if i not in sc: die(f"없는 씬: {i}")
order = [s["id"] for s in jload(p["scenes_v2"])["scenes"]]
if [order.index(i) for i in ids] != list(range(order.index(ids[0]), order.index(ids[0])+len(ids))):
    die("연속된 씬만 묶을 수 있습니다: " + ",".join(ids))

t0 = sc[ids[0]]["t_start"]
def ts(t): return "%02d:%02d:%06.3f" % (int(t//3600), int(t%3600//60), t%60)
out, n = [], 0
for i in ids:
    s = sc[i]; ch = caps[i]
    for k, x in enumerate(ch):
        a0 = s["t_start"] + LEAD + x["start"] - t0
        b0 = s["t_start"] + LEAD + x["end"] + 0.25 - t0
        nxt = s["t_start"] + LEAD + ch[k+1]["start"] - t0 if k+1 < len(ch) else s["t_end"] - t0
        b0 = min(b0, nxt - 0.02); n += 1
        out.append("%d\n%s --> %s\n%s\n" % (n, ts(a0).replace(".", ","), ts(b0).replace(".", ","), x["text"]))
total = sc[ids[-1]]["t_end"] - t0
dst = pathlib.Path(a.out) if a.out else p["edit"]/f"wb_{ids[0]}_{ids[-1]}.srt"
if not dst.is_absolute(): dst = ep/dst
dst.parent.mkdir(parents=True, exist_ok=True)
open(dst, "w").write("\n".join(out))
print(f"{len(ids)}개 씬 {ids[0]}~{ids[-1]} · 자막 {n}줄 · 총 {total:.2f}초 → {dst}")
print(f"본편 삽입 위치: {t0:.2f}s ~ {sc[ids[-1]]['t_end']:.2f}s")
print(f"\n다음 단계: srt-whiteboard-animation 스킬을 이 SRT로 실행. 렌더는 반드시 --no-subtitles")
print(f"  (자막은 Remotion이 이미 화면에 굽는다. 스킬 자막까지 켜면 이중 표시)")
