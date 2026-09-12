#!/usr/bin/env python3
"""**깐 소재가 화면에서 흐려졌나.** 소재는 선명한데 렌더된 칸이 뭉개져 나가는 자리가 있다.

E01 에서 훅 소재가 **233 → 6.6** 으로 떨어진 채 나갔다. 소재를 열어 보면 멀쩡하고
마스터를 멀리서 보면 그럴듯해서, **셈만 맞추는 검사는 전부 통과한다.**

**재는 법 — 같은 크기로 맞춰 놓고 잰다.**
선명도(라플라시안 분산)는 **보는 크기에 따라 통째로 움직인다.** 1920 짜리 소재를 620 칸에
넣으면 줄인 만큼은 원래 떨어지는 게 맞다. 그래서 **소재를 그 칸 크기로 줄여 놓고** 잰 값과
**마스터에서 그 칸을 오려낸** 값을 댄다. 그러면 남는 차이가 「줄여서」가 아니라
「굽다가」 생긴 것이다.

**판정하지 않는다 — 수만 찍는다.** 「얼마나 떨어지면 다시 구워야 하는가」는 미술 값이고
아직 아무도 정한 적이 없다. `62_still_check` 와 같은 자리다.

**언제 선을 긋나 — `E02` 까지 표본을 모은 뒤에 긋는다**(연출).
지금 E01 에서 믿을 수 있는 표본은 **하나**다(70×70 로고). 표본 넷으로 보였던
0.176~1.825 는 **상관을 안 보고 잰 수**라 셋이 딴 데를 재고 있었다.
하나로 그은 선은 선이 아니라 추측이다.

**영상 칸으로 분모를 올리지 않는다**(연출). 어느 프레임인지 못 대는 값은
분모가 아니라 잡음이다 — 분모만 커지고 판정은 더 나빠진다.

`--min-ratio` 를 주면 그때부터 가른다. 기본은 안 가른다.

**칸에서 그 그림을 못 찾으면 안 잰다.** 씬 한가운데 프레임이 그 소재를 안 보여 주는 자리가 많다
(Delay·전환·갈아 끼는 칸). 그때 나온 배수는 흐려진 것이 아니라 **딴 데를 잰 수**다.
실제로 첫 판이 그렇게 속았다 — `s04` 가 「배수 0.176」으로 나와 흐려진 줄 알았는데
**상관이 0.079** 였다(그 칸에 그 그림이 없었다). 상관 바닥(`--min-corr` 0.5)으로 가린다.
그 바닥을 넣자 **잰 칸 4개 → 1개**가 됐다.

**배수를 둘 찍는다.** `배수(원본)` 은 줄이기 전 소재와 대는 것(연출이 말한 233→6.6 = 0.028 이 이것),
`배수(줄인뒤)` 는 칸 크기로 줄인 소재와 대는 것이다. 앞엣것은 **줄인 만큼도 같이 잡히고**
뒤엣것은 **굽다가 잃은 것만** 남는다. 어느 쪽으로 선을 그을지는 정해지지 않았다.

**못 잰 자리는 세어서 찍는다.** 영상 소재는 **어느 프레임인지**를 알아야 대는데 그건
`from`·`stopSec`·`Freeze` 를 따라가야 나온다 — 지금은 그림(png·jpg)만 정확히 댈 수 있다.
영상은 「안 잼」으로 세어서 남긴다. **「걸린 것 0건」과 「본 것이 0건」이 같아 보이면 안 된다.**

종료코드: 0 · 2 설정 오류 · 3 `--min-ratio` 아래가 있음
사용: 64_sharpness_check.py <EP> --master <mp4> [--min-ratio 0.5]
"""
import argparse, pathlib, re, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import FPS, P, REMOTION_DIR, ep_dir, jload, slug  # noqa: E402
from _scene_code import geometry, rect_from_code, scene_body  # noqa: E402

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

ap = argparse.ArgumentParser()
ap.add_argument("ep")
ap.add_argument("--master", required=True)
ap.add_argument("--min-corr", type=float, default=0.5,
                help="이 상관 아래면 「칸에서 그 그림을 못 찾았다」로 보고 안 잰다")
ap.add_argument("--min-ratio", type=float, default=None,
                help="이 배수 아래면 종료코드 3 (안 주면 찍기만 한다 — 선은 미술이 정한다)")
a = ap.parse_args()
ep = ep_dir(a.ep); sl = slug(ep)
master = pathlib.Path(a.master)
if not master.is_file():
    print(f"ERROR: 마스터가 없습니다: {master}", file=sys.stderr); sys.exit(2)
scenes_p = REMOTION_DIR / "src" / sl / "scenes.tsx"
if not scenes_p.is_file():
    print(f"ERROR: 화면 코드가 없습니다: {scenes_p}", file=sys.stderr); sys.exit(2)
scenes_src = scenes_p.read_text(encoding="utf-8")
sc = jload(P(ep)["scenes_v2"])["scenes"]
G = geometry(sl)


def lap_var(arr: np.ndarray) -> float:
    """라플라시안 분산. 흑백 2차원 배열을 받는다."""
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    x = arr.astype(np.float32)
    out = (k[0, 1] * x[:-2, 1:-1] + k[1, 0] * x[1:-1, :-2] + k[1, 1] * x[1:-1, 1:-1]
           + k[1, 2] * x[1:-1, 2:] + k[2, 1] * x[2:, 1:-1])
    return float(out.var())


def corr(x, y):
    x = x.astype("float32").ravel() - x.mean()
    y = y.astype("float32").ravel() - y.mean()
    d = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(x @ y / d) if d else 0.0


def master_frame(t: float) -> Image.Image:
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(master),
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(p.stderr.decode()[:200])
    import io
    return Image.open(io.BytesIO(p.stdout)).convert("L")


rows, unmeasured = [], []
for s in sc:
    sid = s["id"]
    body = scene_body(scenes_src, sid)
    if not body: continue
    for asset in dict.fromkeys(re.findall(r'asset\("([^"]+)"\)', body)):
        src = REMOTION_DIR / "public" / sl / asset
        if not src.is_file():
            unmeasured.append(f"{sid} {asset} — public/{sl}/ 에 파일이 없습니다"); continue
        if not asset.lower().endswith(IMG_EXT):
            unmeasured.append(f"{sid} {asset} — 영상이라 **어느 프레임인지**를 못 댑니다"); continue
        rect, err = rect_from_code(scenes_src, sid, asset, None, G)
        if rect is None:
            unmeasured.append(f"{sid} {asset} — 칸을 못 풉니다 ({err})"); continue
        x, y, w, h = rect
        if w < 8 or h < 8:
            unmeasured.append(f"{sid} {asset} — 칸이 너무 작습니다 ({w}×{h})"); continue
        t = (s["t_start"] + s["t_end"]) / 2
        try:
            fr = master_frame(t)
        except RuntimeError as e:
            unmeasured.append(f"{sid} {asset} — 마스터에서 프레임을 못 떴습니다 ({e})"); continue
        cut = np.asarray(fr.crop((x, y, x + w, y + h)))
        with Image.open(src) as im0:
            im = im0.convert("L"); iw, ih = im.size
            ref = np.asarray(im.resize((w, h), Image.LANCZOS))        # 칸 크기로 줄인 소재
            v_raw = lap_var(np.asarray(im))                           # 줄이기 **전** 소재
            sc_cov = max(w / iw, h / ih)
            rw, rh = max(1, round(iw * sc_cov)), max(1, round(ih * sc_cov))
            cov = np.asarray(im.resize((rw, rh), Image.LANCZOS).crop(
                ((rw - w) // 2, (rh - h) // 2, (rw - w) // 2 + w, (rh - h) // 2 + h)))
        # **닮지 않으면 그 칸에서 그 그림을 못 찾은 것이다.** 안 가리면 「배수 0.18」 같은 수가
        # 나오는데 그건 흐려진 게 아니라 **딴 데를 잰 것**이다. 63 에서 실제로 그렇게 속았다.
        c_best = max(corr(cut, ref), corr(cut, cov))
        if c_best < a.min_corr:
            unmeasured.append(f"{sid} {asset} — 칸에서 그 그림을 못 찾았습니다 "
                              f"(상관 {c_best:.3f} < {a.min_corr})"); continue
        v_m, v_s = lap_var(cut), lap_var(ref)
        ratio = (v_m / v_s) if v_s else float("nan")
        raw_ratio = (v_m / v_raw) if v_raw else float("nan")
        rows.append((sid, asset, w, h, v_s, v_m, ratio, v_raw, raw_ratio))

print(f"칸 선명도 — 마스터 {master.name} · 잰 칸 {len(rows)}개 · 못 잰 것 {len(unmeasured)}개"
      + (f" · 문턱 {a.min_ratio}" if a.min_ratio else " · **판정 안 함**(선은 미술이 정합니다)"))
if rows:
    print(f"  {'씬':5} {'소재':24} {'칸':>11} {'소재원본':>9} {'소재(줄인뒤)':>11} {'마스터':>9} "
          f"{'배수(원본)':>9} {'배수(줄인뒤)':>11}")
    for sid, asset, w, h, vs, vm, r, vraw, rraw in sorted(rows, key=lambda x: x[8]):
        print(f"  {sid:5} {asset[:24]:24} {w:5}×{h:<5} {vraw:9.1f} {vs:11.1f} {vm:9.1f} "
              f"{rraw:9.3f} {r:11.3f}")
    rs = sorted(x[8] for x in rows)
    print(f"  배수(원본) 분포 — 최소 {rs[0]:.3f} · 중앙 {rs[len(rs)//2]:.3f} · 최대 {rs[-1]:.3f}")
for u in unmeasured:
    print(f"  ? {u}")

if a.min_ratio is not None:
    bad = [r for r in rows if r[8] < a.min_ratio]
    if bad:
        print(f"\n  ✕ 배수(원본)가 {a.min_ratio} 아래인 칸 {len(bad)}개", file=sys.stderr)
        for sid, asset, w, h, vs, vm, r, vraw, rraw in bad:
            print(f"    {sid} {asset} 칸 {w}×{h} · 소재 {vraw:.1f} → 마스터 {vm:.1f} (배수 {rraw:.3f})",
                  file=sys.stderr)
        sys.exit(3)
