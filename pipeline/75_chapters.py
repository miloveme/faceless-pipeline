#!/usr/bin/env python3
"""script/chapters.json + scenes_v2 → edit/chapters.txt (첫 챕터는 00:00)

두 꼴을 다 받는다.

    [["s00","실패 테이크"], …]                          ← 옛 꼴. 그대로 돈다
    {"_": ["…설명…"], "chapters": [["s00","…"], …]}     ← 설명을 같이 두는 꼴

**설명 자리(`_`)를 받는 이유**는 이 파일이 순수 배열이면 **왜 그렇게 골랐는지를 적을 데가 없어서**다.
「마지막 장이 s29 다 — 빠진 것이 아니라 뺀 것이다」 같은 것은 **이 파일을 여는 사람이 봐야** 하는데,
대본이나 다른 문서에 적으면 그 사람은 안 본다(작가). `timing.json` 이 같은 꼴을 쓴다.

없는 씬 id 를 주면 **조용히 0시로 가지 않고 죽는다** — 씬 번호가 밀린 판본의 챕터가
그대로 남아 있는 일이 실제로 있었다.

사용: 75_chapters.py <EP>"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
if not p["chapters"].exists(): die("script/chapters.json 없음")
_raw = jload(p["chapters"])
if isinstance(_raw, dict):
    if "chapters" not in _raw: die('chapters.json 이 객체인데 "chapters" 가 없습니다.', 2)
    _ch, _note = _raw["chapters"], len(_raw.get("_") or [])
elif isinstance(_raw, list):
    _ch, _note = _raw, 0
else:
    die("chapters.json 은 배열이거나 {\"_\": […], \"chapters\": […]} 여야 합니다.", 2)

start = {s["id"]: s["t_start"] for s in jload(p["scenes_v2"])["scenes"]}
_miss = [sid for sid, _ in _ch if sid not in start]
if _miss:
    die(f"chapters.json 이 없는 씬을 가리킵니다: {', '.join(_miss)}\n"
        f"  씬 번호가 밀린 판본의 챕터가 남아 있는 자리입니다.\n"
        f"  있는 씬 {len(start)}개: {', '.join(start)}", 3)

lines = [f"{'00:00' if i == 0 else '%02d:%02d' % (int(start[sid] // 60), int(start[sid] % 60))} {name}"
         for i, (sid, name) in enumerate(_ch)]
p["edit"].mkdir(exist_ok=True); open(p["edit"] / "chapters.txt", "w").write("\n".join(lines))
print("\n".join(lines))
# **장 수와 첫 장·마지막 장을 같이 찍는다**(작가 요청) — 그것으로 지금 편과 맞는지 댈 수 있다.
print(f"챕터: **{len(_ch)}장** · 첫 장 {_ch[0][0]} 00:00 · 마지막 장 {_ch[-1][0]} {lines[-1].split()[0]}"
      + (f" · 설명 {_note}줄" if _note else " · 설명 없음"))
