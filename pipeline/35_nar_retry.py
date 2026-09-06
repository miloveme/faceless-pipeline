#!/usr/bin/env python3
"""검사에서 BAD로 나온 씬을 retry_seeds 순서로 재생성하고, 통과하는 첫 테이크로 교체한다.
원본은 <id>_dropped_seed<seed>.mp3로 보관. 교체 후 30_nar_check.py를 해당 씬만 다시 돌린다.
사용: 35_nar_retry.py <EP> --ids s09,s16"""
import argparse, shutil
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", required=True)
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); v = voice_cfg(); readings = readings_for(ep); fixes = whisper_fixes_for(ep)
c = Comfy(v["host"]); ref = {x["id"]: x["text"] for x in jload(p["tts_input"])}
if not c.alive(): die("원격 ComfyUI 응답 없음")
upload_ref(c, v)
for sid in a.ids.split(","):
    ok = False
    for seed in v["retry_seeds"]:
        out = p["nar_raw"]/f"{sid}_seed{seed}.mp3"
        tts_one(c, v, ref[sid], f"{slug(ep)}/{sid}_seed{seed}", out, seed=seed)
        r = check_scene(out, ref[sid], readings, fixes)
        print(sid, "seed", seed, "kind", r["kind"], "cer", r["cer"], "big", r["big"])
        if r["kind"] != "content":
            cur = p["nar_raw"]/f"{sid}.mp3"
            if cur.exists(): shutil.move(cur, p["nar_raw"]/f"{sid}_dropped_seed{v['seed']}.mp3")
            shutil.copy(out, cur); print("  replaced", sid, "with seed", seed); ok = True; break
    if not ok: print("  FAILED all seeds for", sid, "— 문장을 나누거나 표현을 바꿔 다시 시도")
print("이제 30_nar_check.py <EP> --ids", a.ids, "로 bounds를 갱신할 것")
