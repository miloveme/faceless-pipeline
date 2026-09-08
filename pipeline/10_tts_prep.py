#!/usr/bin/env python3
"""1단계 끝 → 2단계 입구. scenes_v1.json의 narration을 TTS용 한글 읽기로 전처리해
narration_tts 필드와 audio/narration_tts_input.json을 만든다.

무엇을 무엇으로 바꿨는지(subs)도 씬별로 남긴다 — 30단계가 숫자 읽기를 받아쓰기와 대조할 때 쓴다.
소리로 못 내는 것이 남으면 종료코드 2 — 영문은 script/tts_overrides.json에 읽기를 추가하고,
기호는 어떻게 읽을지 정해서 사전에 넣거나 대본에서 뺀 뒤 다시 실행.
사용: 10_tts_prep.py <EP> [--ids s01,s02]"""
import sys, argparse
from common import *
# **안 준 것과 빈 것을 가른다.** default 를 "" 로 두면 --ids 를 안 줘도 pick_ids 가
# 「비어 있다」로 죽인다 — 네 스크립트가 다 그랬다(음악 감독이 잡았다). 기본은 None 이다.
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
readings = readings_for(ep)
if not p["scenes_v1"].exists(): die(f"씬 JSON 이 없습니다: {p['scenes_v1']}\n  먼저 05_script_to_scenes.py 를 돌리세요.")
d = jload(p["scenes_v1"]); only = pick_ids(a.ids, {s["id"] for s in d["scenes"]})
tts, unknown, unspeakable = [], {}, {}
for s in d["scenes"]:
    if only and s["id"] not in only: continue
    t, left, bad, subs = tts_preprocess(s["narration"], readings)
    s["narration_tts"] = t
    if left: unknown[s["id"]] = left
    if bad: unspeakable[s["id"]] = bad
    # 어느 판본으로 만들었는지를 산출물에 박는다 — 30·40 이 이걸로 어긋남을 본다
    tts.append({"id": s["id"], "text": t, "subs": subs, "script_sha": script_sha(s["narration"])})
done_ids = {x["id"] for x in tts}
jdump(d, p["scenes_v1"])
if only and p["tts_input"].exists():
    old = {x["id"]: x for x in jload(p["tts_input"])}
    for x in tts: old[x["id"]] = x
    tts = [old[k] for k in sorted(old)]
n_done = len(done_ids)
jdump(tts, p["tts_input"])
n_num = sum(1 for x in tts for s in x.get("subs", []) if s["kind"] == "number")
no_subs = [x["id"] for x in tts if "subs" not in x]
print(f"전처리 {n_done}/{len(d['scenes'])}씬" + (" (--ids 로 일부만)" if only else "")
      + f" · 병합 결과 {len(tts)}씬 {sum(len(x['text']) for x in tts)}자 · 숫자 읽기 {n_num}개 → {p['tts_input']}")
if no_subs:
    print(f"  주의: subs 가 없는 씬 {len(no_subs)}개 — 옛 형식입니다. 그 씬은 30단계의 숫자 대조가 안 돕니다:",
          ", ".join(no_subs))
for x in tts:
    print((" *" if x["id"] in done_ids else "  "), x["id"], x["text"][:70])
    for s in x.get("subs", []):
        if s["kind"] != "reading": print(f"        {s['kind']:6} {s['from']!r} → {s['to']!r}")
if unknown:
    print("\n읽기 사전에 없는 영문 토큰 (script/tts_overrides.json 에 추가):")
    [print(" ", k, v) for k, v in unknown.items()]
if unspeakable:
    print("\n소리로 못 내는 문자가 남았습니다 (한글·숫자·공백·. , ? ! 만 통과합니다):")
    for k, v in unspeakable.items(): print(" ", k, v)
    print("  어떻게 읽을지 정해서 script/tts_overrides.json 에 넣거나, 대본에서 빼세요.")
    print("  그냥 두면 TTS 가 제멋대로 읽거나 조용히 건너뜁니다 — 물결표가 '육, 칠 세'로 끊겨 읽힌 적이 있습니다.")
if unknown or unspeakable: sys.exit(2)
