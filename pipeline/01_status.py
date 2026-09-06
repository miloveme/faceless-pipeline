#!/usr/bin/env python3
"""작업 전 점검 — 서버 연결, 큐, 그리고 이 에피소드에 무엇이 남았는지.

사용: 01_status.py [<EP>]
"""
import argparse, sys
from common import *
from hosts import plan

ap = argparse.ArgumentParser(); ap.add_argument("ep", nargs="?")
a = ap.parse_args()
v = voice_cfg()
if v.get("_provider") != "comfyui_chatterbox":
    print(f"음성 제공자: {v['_provider']} (서버 확인은 자체 호스팅 ComfyUI 일 때만)")


if not a.ep:
    if v.get("_provider") == "comfyui_chatterbox": plan(v, n_items=1, verbose=True)
    sys.exit(0)

ep = ep_dir(a.ep); p = P(ep)
tts = jload(p["tts_input"]) if p["tts_input"].exists() else []
ids = {x["id"] for x in tts}
done = {i for i in ids if (p["nar_raw"]/f"{i}.mp3").exists()} if p["nar_raw"].exists() else set()
todo = [x for x in tts if x["id"] not in done]
chars = sum(len(x["text"]) for x in todo)

print(f"에피소드 {ep.name}")
print(f"  대본 {len(tts)}씬 · 생성됨 {len(done)} · 남음 {len(todo)}" + (f" ({chars}자)" if todo else ""))
for step, path, label in [
    ("05", p["scenes_v1"], "씬 JSON"), ("10", p["tts_input"], "읽기 전처리"),
    ("30", p["nar_raw"]/"whisper_cer.json", "검사 결과"), ("40", p["scenes_v2"], "시각표"),
    ("45", ep/"script"/"visual_plan.md", "화면 계획"), ("50", p["caps"], "자막"),
]:
    print(f"  {step} {label:12} {'있음' if path.exists() else '없음'}")
print()
if todo and v.get("_provider") == "comfyui_chatterbox":
    plan(v, n_items=len(todo), total_chars=chars, verbose=True)
elif todo:
    print(f"남은 {len(todo)}씬을 {v['_provider']} 로 생성합니다.")
else:
    print("생성할 씬이 없습니다.")
