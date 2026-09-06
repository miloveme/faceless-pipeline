#!/usr/bin/env python3
"""화면 녹화를 내레이션에 붙인다 — 앵커 기준 구간별 배속·컷·프리즈.

구성된 화면(표·도식)은 자기 시간이 없어서 음성이 길이를 정한다.
녹화는 다르다. 0:12에 렌더가 시작되고 1:05에 에러가 뜬다 — 안쪽에 고정된 구조가 있다.
전 구간을 맞추려 하면 한쪽이 망가지므로, **몇 지점만 못 박고 사이를 늘였다 줄인다.**

읽는 것
  script/rec_sync.json      어느 씬에 어느 녹화를 붙이고, 어느 앵커가 어느 자막 줄에 붙나
  source/<이름>.anchors.json 녹화 안의 지점들
  script/captions.json      그 자막 줄이 언제 발화되는지 (이미 있다)
남기는 것
  <Remotion>/src/<slug>/data/rec_<씬>.json   구간표
  <Remotion>/public/<slug>/rec/<씬>_f<n>.png 프리즈용 정지 프레임

사용: 48_rec_sync.py <EP> [--max-speed 3.0] [--min-speed 0.85]
"""
import argparse
from common import *

ap = argparse.ArgumentParser(); ap.add_argument("ep")
ap.add_argument("--max-speed", type=float, default=3.0,
                help="이 배속을 넘겨야 맞출 수 있으면 뒤를 잘라낸다. 3배 넘으면 커서가 순간이동해 보인다")
ap.add_argument("--min-speed", type=float, default=0.85,
                help="이보다 느리게는 늦추지 않는다. 화면 녹화 슬로우모션은 어색하다. 대신 끝에서 멈춘다")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); sl = slug(ep)

cfg_path = ep / "script" / "rec_sync.json"
if not cfg_path.exists():
    die(f"{cfg_path} 없음.\n"
        '예) {"s09": {"clip": "rec/blender.mp4", "anchors": "source/blender.anchors.json",\n'
        '            "bind": [{"anchor": "render_start", "line": 1}, {"anchor": "error", "line": 3}]}}')
cfg = jload(cfg_path)
caps = jload(p["caps"]); scenes = {s["id"]: s for s in jload(p["scenes_v2"])["scenes"]}
data_dir = REMOTION_DIR / "src" / sl / "data"
pub = REMOTION_DIR / "public" / sl
still_dir = pub / "rec"
data_dir.mkdir(parents=True, exist_ok=True); still_dir.mkdir(parents=True, exist_ok=True)

def clip_len(f):
    return dur(f)

problems, made = [], []
for sid, c in cfg.items():
    if sid not in scenes: die(f"없는 씬: {sid}")
    sc = scenes[sid]; scene_dur = sc["t_end"] - sc["t_start"]
    lines = caps.get(sid) or die(f"{sid} 자막이 없습니다. 50단계를 먼저 돌리세요.")

    cp = pathlib.Path(c["clip"]); src = cp if cp.is_absolute() else ep / cp
    if not src.exists(): die(f"녹화 파일 없음: {src}")
    total = clip_len(src)
    # 녹화를 Remotion public 으로 옮긴다. 소리는 뺀다 — 내레이션이 따로 있다.
    pub_name = f"rec_{src.stem}.mp4"
    dst = pub / pub_name
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an",
             "-vf", "scale=1920:-2", "-c:v", "libx264", "-crf", "20", "-preset", "fast", str(dst)])

    an = pathlib.Path(c["anchors"]); apath = an if an.is_absolute() else ep / an
    if not apath.exists(): die(f"앵커 파일 없음: {apath}")
    anchors = {x["id"]: float(x["t"]) for x in jload(apath)["anchors"]}

    # 못 박을 짝: (녹화 안의 시각, 씬 안의 시각)
    pins = [(0.0, 0.0)]
    for b in c["bind"]:
        if b["anchor"] not in anchors: die(f"{sid}: 앵커 '{b['anchor']}' 가 {apath} 에 없습니다")
        i = b["line"]
        if i >= len(lines): die(f"{sid}: 자막 {i}번 줄이 없습니다 (총 {len(lines)}줄)")
        pins.append((anchors[b["anchor"]], LEAD + lines[i]["start"]))
    end_clip = float(c.get("clip_end", total))
    pins.append((min(end_clip, total), scene_dur))
    pins.sort()
    for (c1, s1), (c2, s2) in zip(pins, pins[1:]):
        if c2 <= c1 or s2 <= s1:
            die(f"{sid}: 앵커 순서가 뒤집혔습니다 (녹화 {c1:.2f}→{c2:.2f}, 씬 {s1:.2f}→{s2:.2f})")

    segs = []
    for (c1, s1), (c2, s2) in zip(pins, pins[1:]):
        cs, ss = c2 - c1, s2 - s1
        speed = cs / ss
        if speed > a.max_speed:
            # 너무 길다 — 최대 배속으로 갈 수 있는 만큼만 보여주고 나머지는 잘라낸다
            used = a.max_speed * ss
            segs.append({"kind": "play", "clipFrom": round(c1, 3), "clipTo": round(c1 + used, 3),
                         "from": round(s1, 3), "to": round(s2, 3), "speed": a.max_speed,
                         "cutSec": round(cs - used, 2)})
        elif speed < a.min_speed:
            # 너무 짧다 — 최저 배속으로 늦추고, 남는 시간은 마지막 프레임으로 멈춘다
            play_s = cs / a.min_speed
            segs.append({"kind": "play", "clipFrom": round(c1, 3), "clipTo": round(c2, 3),
                         "from": round(s1, 3), "to": round(s1 + play_s, 3), "speed": a.min_speed})
            segs.append({"kind": "freeze", "at": round(c2, 3),
                         "from": round(s1 + play_s, 3), "to": round(s2, 3)})
        else:
            segs.append({"kind": "play", "clipFrom": round(c1, 3), "clipTo": round(c2, 3),
                         "from": round(s1, 3), "to": round(s2, 3), "speed": round(speed, 4)})

    # 프리즈 정지 프레임을 뽑아 둔다 (배속 0 으로 세우는 것보다 확실하다)
    for n, sg in enumerate(x for x in segs if x["kind"] == "freeze"):
        out = still_dir / f"{sid}_f{n}.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(sg["at"]), "-i", str(src),
             "-frames:v", "1", str(out)])
        sg["still"] = f"{sl}/rec/{out.name}"

    # 검사: 앵커가 제 문장에 붙었나, 구간이 씬을 빈틈없이 덮나
    for b in c["bind"]:
        want = LEAD + lines[b["line"]]["start"]
        got = next((sg["from"] for sg in segs if abs(sg["from"] - want) < 1e-6), None)
        if got is None:
            problems.append(f"{sid}: 앵커 '{b['anchor']}' 가 구간 경계에 없습니다")
    cov = 0.0
    for sg in segs: cov += sg["to"] - sg["from"]
    if abs(cov - scene_dur) > 0.05:
        problems.append(f"{sid}: 구간 합 {cov:.2f}s 가 씬 길이 {scene_dur:.2f}s 와 다릅니다")

    jdump({"scene": sid, "clip": f"{sl}/{pub_name}", "segments": segs},
          data_dir / f"rec_{sid}.json")
    made.append((sid, segs, scene_dur))

for sid, segs, sd in made:
    print(f"{sid}  씬 {sd:.2f}s · 구간 {len(segs)}개")
    for sg in segs:
        if sg["kind"] == "play":
            cut = f" · {sg['cutSec']}s 잘라냄" if sg.get("cutSec") else ""
            print(f"    {sg['from']:6.2f}~{sg['to']:6.2f}s  녹화 {sg['clipFrom']:6.2f}~{sg['clipTo']:6.2f}s"
                  f"  ×{sg['speed']:.2f}{cut}")
        else:
            print(f"    {sg['from']:6.2f}~{sg['to']:6.2f}s  멈춤 (녹화 {sg['at']:.2f}s)")
print()
if problems:
    print("검사에 걸린 것"); [print("  ✕", x) for x in problems]; sys.exit(3)
print(f"○ 앵커가 전부 제 문장에 붙었고 구간이 씬을 빈틈없이 덮습니다 → {data_dir}")
