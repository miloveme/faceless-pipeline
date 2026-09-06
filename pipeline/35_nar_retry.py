#!/usr/bin/env python3
"""검사에서 BAD 로 나온 씬을 다시 만들어 통과하는 첫 결과로 교체한다.
시드를 지원하는 제공자는 시드만 바꾼다(설정을 건드리면 목소리가 달라진다).
원본은 <id>_dropped_N.mp3 로 보관. 교체 후 30 단계를 그 씬만 다시 돌린다.

사용: 35_nar_retry.py <EP> --ids s09,s16 [--tries 3]
"""
import argparse, shutil
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", required=True)
ap.add_argument("--tries", type=int, default=3)
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); cfg = voice_cfg()
readings = readings_for(ep); fixes = whisper_fixes_for(ep)
ref = {x["id"]: x["text"] for x in jload(p["tts_input"])}
print(f"제공자: {cfg['_provider']}")
for sid in a.ids.split(","):
    ok = False
    for attempt in range(1, a.tries + 1):
        out = p["nar_raw"]/f"{sid}_try{attempt}.mp3"
        tts_generate(ref[sid], out, cfg, attempt=attempt)
        r = check_scene(out, ref[sid], readings, fixes)
        print(f"  {sid} 시도 {attempt}: {r['kind']} cer {r['cer']} {r['big'] if r['big'] else ''}")
        if r["kind"] != "content":
            cur = p["nar_raw"]/f"{sid}.mp3"
            if cur.exists(): shutil.move(cur, p["nar_raw"]/f"{sid}_dropped_0.mp3")
            shutil.copy(out, cur); print(f"    → {sid} 교체 (시도 {attempt})"); ok = True; break
    if not ok:
        print(f"    {sid} 실패 — 문장을 나누거나 표현을 바꿔 보세요")
print("이제 30_nar_check.py <EP> --ids", a.ids, "로 bounds 를 갱신하세요")
