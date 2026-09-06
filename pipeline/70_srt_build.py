#!/usr/bin/env python3
"""captions.json + scenes_v2 → edit/<PREFIX>_episode_ko.srt, 그리고 script/captions_en.json이 있으면 _en.srt.
영어 JSON은 씬별 청크 수가 한국어와 같아야 한다(1:1 타이밍). 사용: 70_srt_build.py <EP>"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
c = jload(p["caps"]); s = jload(p["scenes_v2"])["scenes"]; prefix = ep.name.split("_")[0]
def ts(t): return "%02d:%02d:%06.3f" % (int(t//3600), int(t%3600//60), t%60)
def build(lang, en=None):
    out, n = [], 0
    for sc in s:
        ch = c[sc["id"]]
        for i, x in enumerate(ch):
            a0 = sc["t_start"]+LEAD+x["start"]; b0 = sc["t_start"]+LEAD+x["end"]+0.25
            nxt = sc["t_start"]+LEAD+ch[i+1]["start"] if i+1 < len(ch) else sc["t_end"]
            b0 = min(b0, nxt-0.02); n += 1
            out.append("%d\n%s --> %s\n%s\n" % (n, ts(a0).replace(".",","), ts(b0).replace(".",","), x["text"] if lang=="ko" else en[sc["id"]][i]))
    return "\n".join(out)
p["edit"].mkdir(exist_ok=True)
open(p["edit"]/f"{prefix}_episode_ko.srt","w").write(build("ko")); print("ko srt ok")
if p["caps_en"].exists():
    en = jload(p["caps_en"])
    for sc in s:
        if len(c[sc["id"]]) != len(en.get(sc["id"], [])): die(f"영어 청크 수 불일치 {sc['id']}: ko {len(c[sc['id']])} en {len(en.get(sc['id'],[]))}")
    open(p["edit"]/f"{prefix}_episode_en.srt","w").write(build("en", en)); print("en srt ok")
else: print("captions_en.json 없음 → 영어 SRT 생략 (씬별 청크 수를 맞춰 번역 JSON을 만들면 생성됨)")
for f in p["edit"].glob(f"{prefix}_episode_*.srt"):
    run(["ffmpeg","-v","error","-i",str(f),"-f","srt","-"], stdout=subprocess.DEVNULL); print("parsed", f.name)
