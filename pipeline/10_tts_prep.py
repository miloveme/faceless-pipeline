#!/usr/bin/env python3
"""1단계 끝 → 2단계 입구. scenes_v1.json의 narration을 TTS용 한글 읽기로 전처리해
narration_tts 필드와 audio/narration_tts_input.json을 만든다.
사전에 없는 영문 토큰이 남으면 종료코드 2 — script/tts_overrides.json에 읽기를 추가하고 다시 실행.
사용: 10_tts_prep.py <EP> [--ids s01,s02]"""
import sys, argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default="")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
readings = readings_for(ep); d = jload(p["scenes_v1"]); only = set(a.ids.split(",")) if a.ids else None
tts, unknown = [], {}
for s in d["scenes"]:
    if only and s["id"] not in only: continue
    t, left = tts_preprocess(s["narration"], readings)
    s["narration_tts"] = t
    if left: unknown[s["id"]] = left
    tts.append({"id": s["id"], "text": t})
jdump(d, p["scenes_v1"])
if only and p["tts_input"].exists():
    old = {x["id"]: x for x in jload(p["tts_input"])}
    for x in tts: old[x["id"]] = x
    tts = [old[k] for k in sorted(old)]
jdump(tts, p["tts_input"])
print(f"{len(tts)} scenes, {sum(len(x['text']) for x in tts)} chars → {p['tts_input']}")
for x in tts: print(" ", x["id"], x["text"][:70])
if unknown:
    print("\n읽기 사전에 없는 영문 토큰 (script/tts_overrides.json에 추가):"); [print(" ", k, v) for k, v in unknown.items()]; sys.exit(2)
