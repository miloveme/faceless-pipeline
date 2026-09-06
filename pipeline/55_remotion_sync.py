#!/usr/bin/env python3
"""에피소드 데이터를 Remotion 프로젝트로 복사: public/<slug>/nar/<id>.mp3, src/<slug>/data/{scenes_v2,captions}.json
사용: 55_remotion_sync.py <EP>"""
import argparse, shutil
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); sl = slug(ep)
pub = REMOTION_DIR/"public"/sl; data = REMOTION_DIR/"src"/sl/"data"; (pub/"nar").mkdir(parents=True, exist_ok=True); data.mkdir(parents=True, exist_ok=True)
if not p["scenes_v2"].exists(): die("scenes_v2.json 이 없습니다 — 먼저 40_nar_finalize.py 를 돌리세요.")
if not p["caps"].exists(): die("captions.json 이 없습니다 — 먼저 50_captions_build.py 를 돌리세요.")
sc = jload(p["scenes_v2"])
for s in sc["scenes"]:
    run(["ffmpeg","-v","error","-y","-i",str(ep/s["narration_file"]),"-b:a","192k",str(pub/"nar"/f"{s['id']}.mp3")])
shutil.copy(p["scenes_v2"], data/"scenes_v2.json"); jdump(jload(p["caps"]), data/"captions.json", indent=None)
print("synced", len(sc["scenes"]), "nar →", pub/"nar", "| data →", data)
