#!/usr/bin/env python3
"""source 클립을 Remotion public/<slug>로 1080p 무음 복사, 정지 프레임, 컨택트 시트(크롭·강조 테두리).
설정: script/visual_prep.json
{"clips":{"take_fail":"take_C_1436_noRig.mp4","take_fix":"take_D_1503_rigLock.mp4"},
 "stills":{"take_fail":[0,7,12.9],"take_fix":[0,7,12.9]},
 "contact":[{"name":"contact_crop","src":"take_fail","every_sec":1.5,"count":9,"crop":[0.05,0,0.55,0.7],"highlight":[3,4,5,6],"cell_w":400}]}
사용: 15_clip_prep.py <EP>"""
import argparse
from common import *
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
cfg = jload(p["visual_prep"]); pub = REMOTION_DIR/"public"/slug(ep); pub.mkdir(parents=True, exist_ok=True)
for name, src in cfg.get("clips", {}).items():
    run(["ffmpeg","-v","error","-y","-i",str(ep/"source"/src),"-vf","scale=1920:-2","-c:v","libx264","-crf","18","-preset","fast","-an",str(pub/f"{name}.mp4")]); print("clip", name, f"{dur(pub/f'{name}.mp4'):.1f}s")
for name, times in cfg.get("stills", {}).items():
    for t in times:
        run(["ffmpeg","-v","error","-y","-ss",str(t),"-i",str(pub/f"{name}.mp4"),"-frames:v","1",str(pub/f"{name.replace('take_','')}_{t}.png")])
def sheet(imgs, cw, gap, hl, every):
    ch = int(cw*imgs[0].size[1]/imgs[0].size[0]); n = len(imgs)
    sh = Image.new("RGB",(n*cw+(n+1)*gap, ch+2*gap+44),(15,17,21)); d = ImageDraw.Draw(sh)
    try: f = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc",24)
    except Exception: f = ImageFont.load_default()
    for i, im in enumerate(imgs):
        x = gap+i*(cw+gap); y = gap+44; sh.paste(im.resize((cw,ch)),(x,y))
        if i in hl: d.rectangle((x-4,y-4,x+cw+3,y+ch+3),outline=(229,72,77),width=6)
        d.text((x+8,gap+8),f"{i*every:.1f}s",fill=(200,200,200),font=f)
    return sh
for c in cfg.get("contact", []):
    frames = []
    for i in range(c["count"]):
        tmp = f"/tmp/_cs_{i}.png"; run(["ffmpeg","-v","error","-y","-ss",str(i*c["every_sec"]),"-i",str(pub/f"{c['src']}.mp4"),"-frames:v","1",tmp]); frames.append(Image.open(tmp))
    W, H = frames[0].size; x0,y0,x1,y1 = c.get("crop",[0,0,1,1])
    imgs = [im.crop((int(W*x0),int(H*y0),int(W*x1),int(H*y1))) for im in frames]
    sheet(imgs, c.get("cell_w",400), 10, set(c.get("highlight",[])), c["every_sec"]).save(pub/f"{c['name']}.png"); print("contact", c["name"])
print("→", pub)
