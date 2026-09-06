#!/usr/bin/env python3
"""script/chapters.json [["s00","실패 테이크"],...] + scenes_v2 → edit/chapters.txt (첫 챕터는 00:00)"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
if not p["chapters"].exists(): die("script/chapters.json 없음")
start = {s["id"]: s["t_start"] for s in jload(p["scenes_v2"])["scenes"]}
lines = [f"{'00:00' if i==0 else '%02d:%02d' % (int(start[sid]//60), int(start[sid]%60))} {name}" for i,(sid,name) in enumerate(jload(p["chapters"]))]
p["edit"].mkdir(exist_ok=True); open(p["edit"]/"chapters.txt","w").write("\n".join(lines)); print("\n".join(lines))
