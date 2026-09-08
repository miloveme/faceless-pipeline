#!/usr/bin/env python3
"""source/ 의 소재를 Remotion 이 쓸 수 있는 형태로 public/<slug>/ 에 넣는다.

소재가 어디서 왔든(화면 녹화, AI 생성, 기존 프로젝트, 내려받은 이미지) 전부 source/ 에 두고
여기서 한 번에 정리한다. → docs/VISUALS.md

설정: script/visual_prep.json
{
  "clips":  {"take_fail": "raw_take_a.mp4"},              영상: 1080p 무음으로 변환
  "images": {"diagram": "sketch.png", "shot": "still.jpg"}, 이미지: 가로 1920 이하로 맞춰 복사
  "stills": {"take_fail": [0, 7, 12.9]},                  영상에서 정지 프레임 뽑기
  "crops":  {"hook_left": {"src":"hook_compare","t":7.8,"box":[0,0,960,380]}},  일부만 잘라 새 이미지로
                                                          (t 는 영상일 때만. box 는 변환본 픽셀 [x0,y0,x1,y1])
  "contact":[{"name":"contact_crop","src":"take_fail","every_sec":1.5,"count":9,
              "crop":[0.05,0,0.55,0.7],"highlight":[3,4,5,6],"cell_w":400}]   여러 장 한 화면에
}
사용: 15_clip_prep.py <EP>"""
import argparse
from common import *
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
cfg = jload(p["visual_prep"]); pub = REMOTION_DIR/"public"/slug(ep); pub.mkdir(parents=True, exist_ok=True)
# 소재는 편의 source/ 에서 온다. 여러 편이 같이 쓰는 것(로고·아이콘)만 `assets/…` 로 적는다 —
# 편마다 복사하면 채널 얼굴이 편마다 갈린다.
def _src_of(fn):
    return (CHANNEL/fn) if fn.startswith("assets/") else (ep/"source"/fn)

for name, v in cfg.get("clips", {}).items():
    c = prep_entry(v); src = _src_of(c["src"])
    if not src.exists(): die(f'clips "{name}": 소재가 없습니다 — {src}')
    # 시간 자르기 → **화면 자르기** → 가리기 → 크기 순서다.
    # crop 이 mask 보다 **앞**이라 mask 의 정규화 좌표는 **잘라낸 뒤** 기준이다 — ffmpeg 의 iw/ih 가
    # 그 필터에 들어오는 그림을 가리키기 때문이다. 크기(scale)를 먼저 바꾸면 좌표가 안 맞는다.
    pre = ["-ss", str(c["ss"])] if c.get("ss") is not None else []
    post = ["-t", str(c["t"])] if c.get("t") is not None else []
    crop = ""
    if c.get("crop"):
        cx, cy, cw, ch = c["crop"]                      # 소재 픽셀 [x, y, w, h]
        crop = f"crop={cw}:{ch}:{cx}:{cy},"
    box = "".join(f"drawbox=x=iw*{x}:y=ih*{y}:w=iw*{w}:h=ih*{h}:color=black@1:t=fill," for x, y, w, h in c.get("mask", []))
    # 소리는 기본으로 뺀다 — 내레이션이 담당한다. 원본 소리가 필요한 자리(인트로)만 audio:true 로 남긴다.
    au = ["-c:a","aac","-b:a","192k"] if c.get("audio") else ["-an"]
    run(["ffmpeg","-nostdin","-v","error","-y"] + pre + ["-i", str(src)] + post +
        ["-vf", crop+box+"scale=1920:-2", "-c:v","libx264","-crf","18","-preset","fast"] + au + [str(pub/f"{name}.mp4")])
    got = dur(pub/f"{name}.mp4")
    if c.get("t") is not None and abs(got - float(c["t"])) > 0.05:
        die(f'clips "{name}": {c["t"]}초를 지정했는데 {got:.3f}초가 나왔습니다 — 소재가 그만큼 없거나 ss 가 너무 뒤입니다 ({src})', 3)
    _wh = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height",
                          "-of","csv=p=0",str(pub/f"{name}.mp4")], capture_output=True, text=True).stdout.strip()
    print("clip", name, f"{got:.3f}s", _wh, "소리있음" if c.get("audio") else "무음",
          (f'잘라냄 {c["crop"]}' if c.get("crop") else ""),
          (f'가림 {len(c.get("mask", []))}칸' if c.get("mask") else ""))
for name, v in cfg.get("images", {}).items():
    s = _src_of(prep_entry(v)["src"])
    if not s.exists(): die(f"이미지가 없습니다: {s}")
    im = Image.open(s); im = im.convert("RGB") if im.mode not in ("RGB", "RGBA") else im
    if im.width > 1920: im = im.resize((1920, round(im.height*1920/im.width)), Image.LANCZOS)
    out = pub/f"{name}.png"; im.save(out)
    print("image", name, f"{im.width}x{im.height}")

# 클립 끝을 넘겨 찍으면 ffmpeg 이 **종료코드 0 으로 아무것도 안 만든다.** 그러면 그 스틸을
# 쓰는 화면이 404 로 죽거나(운이 좋으면) 옛 파일이 그대로 남아 조용히 나간다.
for name, times in cfg.get("stills", {}).items():
    src = pub/f"{name}.mp4"
    if not src.exists(): die(f'stills "{name}": 클립이 없습니다 — {src} (clips 에 먼저 넣으세요)')
    d = dur(src)
    for t in times:
        if float(t) >= d:
            die(f'stills "{name}": {t}초는 클립 끝({d:.3f}초)을 넘습니다 — 아무것도 안 나옵니다.\n'
                f'  마지막 프레임을 원하면 끝보다 최소 한 프레임 앞을 주세요.', 3)
        out = pub/f"{name.replace('take_','')}_{t}.png"
        run(["ffmpeg","-nostdin","-v","error","-y","-ss",str(t),"-i",str(src),"-frames:v","1",str(out)])
        if not out.exists() or out.stat().st_size == 0:
            die(f'stills "{name}" @{t}초: 파일이 안 나왔습니다 — {out}', 3)
        print("still", out.name, f"@{t}s")
# 잘라낸 그림. 좌우가 한 장에 붙어 있는 대조 소재에서 한쪽만 쓰고 싶을 때 쓴다.
# 부품에서 자르지 않고 여기서 파일로 만드는 이유 — 부품에서 자르려면 소재의 원본 크기를
# 코드에 적어야 하고, 소재를 다시 자르면 그 숫자가 조용히 틀린다.
for name, c in cfg.get("crops", {}).items():
    src = c["src"]; mp4, png = pub/f"{src}.mp4", pub/f"{src}.png"
    if mp4.exists():
        if "t" not in c: die(f'crops "{name}": 영상이 소재이므로 t(초)가 있어야 합니다 — {mp4}')
        tmp = pub/f"_crop_{name}.png"
        run(["ffmpeg","-nostdin","-v","error","-y","-ss",str(c["t"]),"-i",str(mp4),"-frames:v","1",str(tmp)])
        im = Image.open(tmp); origin = f'{src}.mp4 @{c["t"]}s'
    elif png.exists():
        im = Image.open(png); tmp = None; origin = f"{src}.png"
    else:
        die(f'crops "{name}": 소재가 없습니다 — {mp4} 도 {png} 도 없습니다')
    x0, y0, x1, y1 = c["box"]
    # 범위를 벗어난 상자는 PIL 이 검정으로 메운다 — 조용히 어긋난 그림이 나가므로 여기서 죽는다
    if not (0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height):
        die(f'crops "{name}": 상자 {c["box"]} 가 소재 {im.width}x{im.height} 를 벗어납니다 ({origin})')
    out = pub/f"{name}.png"; im.convert("RGB").crop((x0, y0, x1, y1)).save(out)
    if tmp: tmp.unlink()
    print("crop", name, f"{x1-x0}x{y1-y0}", "←", origin)

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
