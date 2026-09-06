#!/usr/bin/env python3
"""설정된 음성 제공자로 씬별 내레이션 생성 → audio/nar_raw/<id>.mp3

어느 서비스를 쓸지는 pipeline/voice.json 의 provider 가 정한다.
제공자를 바꿔도 이 스크립트와 이후 단계는 그대로다(docs/VOICE_PROVIDERS.md).

사용: 20_tts_generate.py <EP> [--ids s01,s02] [--attempt N]
"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default="")
ap.add_argument("--attempt", type=int, default=0, help="0=기본 설정, 1 이상=재시도(시드 등을 바꾼다)")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); cfg = voice_cfg()
tts = jload(p["tts_input"]); only = set(a.ids.split(",")) if a.ids else None
p["nar_raw"].mkdir(parents=True, exist_ok=True)
times_path = p["nar_raw"]/"exec_times.json"
times = jload(times_path) if times_path.exists() else {}
print(f"제공자: {cfg['_provider']}")
t0 = time.time()
for x in tts:
    if only and x["id"] not in only: continue
    out = p["nar_raw"]/f"{x['id']}.mp3"
    ex = tts_generate(x["text"], out, cfg, attempt=a.attempt)
    times[x["id"]] = ex
    print(f"  {x['id']} ok {dur(out):.1f}s" + (f" (생성 {ex}s)" if ex else ""), flush=True)
jdump(times, times_path)
print("총", round(time.time()-t0), "초")
