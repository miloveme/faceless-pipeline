#!/usr/bin/env python3
"""원격 ComfyUI Chatterbox로 씬별 내레이션 생성 → audio/nar_raw/<id>.mp3, exec_times.json
채널 보이스(_voice/voice.json)로 고정. 참조 음성은 매번 업로드(덮어쓰기)해 원격 input 폴더 상태에 의존하지 않는다.
사용: 20_tts_generate.py <EP> [--ids s01,s02] [--seed N]"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default=""); ap.add_argument("--seed", type=int)
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); v = voice_cfg()
c = Comfy(v["host"])
if not c.alive(): die(f"원격 ComfyUI 응답 없음: {v['host']} (TCP로 확인: nc -vz host port)")
upload_ref(c, v)
tts = jload(p["tts_input"]); only = set(a.ids.split(",")) if a.ids else None
p["nar_raw"].mkdir(parents=True, exist_ok=True)
times = jload(p["nar_raw"]/"exec_times.json") if (p["nar_raw"]/"exec_times.json").exists() else {}
t0 = time.time()
for x in tts:
    if only and x["id"] not in only: continue
    out = p["nar_raw"] / f"{x['id']}.mp3"
    ex = tts_one(c, v, x["text"], f"{slug(ep)}/{x['id']}", out, seed=a.seed)
    times[x["id"]] = ex; print(x["id"], f"ok {dur(out):.1f}s exec {ex}s", flush=True)
jdump(times, p["nar_raw"]/"exec_times.json")
print("wall", round(time.time()-t0), "s")
