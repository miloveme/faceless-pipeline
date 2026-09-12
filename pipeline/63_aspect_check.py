#!/usr/bin/env python3
"""**칸에 넣은 그림이 늘어나 있나.** 소재의 비와 칸의 비가 다른데 늘려 채우면 얼굴이 늘어난다.

E01 s03 에서 **가로가 2.02배 늘어난 채 나갔고 사용자가 찾았다.** 담당 다섯이 다 통과시켰다 —
켜진 화소도 · 대비도 · 안전영역도 전부 통과한다. **「이 비가 무엇의 비인가」를 아무도 안 물었다.**
소재 한 장은 `956×572`(비 1.671)인데 화면에 오는 것은 **한 쪽**(`478×572`, 비 0.8357)이었다.
전체 비로 칸을 잡아 `794×470` 을 줬고, 그래서 가로로 2.02배가 됐다.

**늘어날 수 있는 자리는 한 종류뿐이다** — `objectFit: "fill"`. `contain`·`cover` 는
비가 달라도 레터박스를 만들거나 잘라낼 뿐 **안 늘어난다.** 그래서 이 검사는
`fill` 을 쓰는 부품의 호출만 본다. 찾는 범위를 넓히지 않는다.

**이 문턱은 미술 값이 아니다.** 「늘어남」은 취향이 아니라 기하다 —
맞는 자리는 실측 **0.02%·0.13%** 로 맞았고 틀린 자리는 **102%** 였다. 그 사이가 비어 있어
문턱이 크게 중요하지 않다. 2% 를 쓴다(렌더 반올림과 lerp 양 끝의 흔들림을 덮는다).

**못 푼 칸은 세어서 찍는다.** 칸 크기가 코드에서 안 풀리면 조용히 통과시키지 않는다 —
「걸린 것 0건」과 「본 것이 0건」이 같아 보이면 안 된다.

종료코드: 0 통과 · 2 설정 오류 · 3 늘어난 칸이 있음
사용: 63_aspect_check.py <EP> [--tol 0.02]
"""
import argparse, pathlib, re, sys
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import REMOTION_DIR, ep_dir, slug  # noqa: E402
from _scene_code import _AT, _locals_of, _val, copy_block, geometry, scene_body  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("ep")
ap.add_argument("--tol", type=float, default=0.02,
                help="칸 비와 소재 비의 허용 차 (기본 0.02 = 2%%)")
a = ap.parse_args()
ep = ep_dir(a.ep); sl = slug(ep)
SRC = REMOTION_DIR / "src" / sl
if not SRC.is_dir():
    print(f"ERROR: 화면 코드가 없습니다: {SRC}", file=sys.stderr); sys.exit(2)

parts_p, scenes_p = SRC / "parts.tsx", SRC / "scenes.tsx"
for _p in (parts_p, scenes_p):
    if not _p.is_file():
        print(f"ERROR: {_p} 가 없습니다", file=sys.stderr); sys.exit(2)
parts_src = parts_p.read_text(encoding="utf-8")
scenes_src = scenes_p.read_text(encoding="utf-8")
copy_src = (SRC / "copy.ts").read_text(encoding="utf-8") if (SRC / "copy.ts").is_file() else ""

# ── ① 늘리는 부품을 찾는다 ──────────────────────────────────────────────
# `export const <이름>: React.FC<…> = …` 블록 안에 `objectFit: "fill"` 이 있으면 그 부품이다.
#
# **주석을 먼저 걷어낸다.** 안 걷으면 `Label` 이 걸린다 — 그 뒤에 오는 `CropPlate` 설명
# 주석이 `objectFit: "fill"` 이라는 **글자**를 담고 있고 그게 `Label` 블록 끝에 붙어 있다.
# 실제로 한 번 그렇게 세어서 「늘리는 부품 2종」이 나왔다(진짜는 하나다).
def _decomment(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)

FILL = []
for m in re.finditer(r"^export const (\w+): React\.FC", parts_src, re.M):
    nxt = re.search(r"^export const ", parts_src[m.end():], re.M)
    body = parts_src[m.start(): m.end() + (nxt.start() if nxt else len(parts_src))]
    if re.search(r'objectFit:\s*"fill"', _decomment(body)):
        FILL.append(m.group(1))
if not FILL:
    print(f"칸 비 검사: `objectFit: \"fill\"` 을 쓰는 부품이 {parts_p.name} 에 없습니다 — "
          f"늘어날 수 있는 자리가 없습니다 (본 부품 "
          f"{len(re.findall(r'^export const \w+: React.FC', parts_src, re.M))}개)")
    sys.exit(0)

# ── ② 그 부품의 호출을 전부 모은다 ──────────────────────────────────────
CALL = re.compile(r"<(" + "|".join(FILL) + r")\s+src=\{asset\(\"([^\"]+)\"\)\}\s*"
                  r"crop=\{\{([^}]*)\}\}", re.S)
uses = list(CALL.finditer(scenes_src))
scene_at = [(m.group(1), m.start()) for m in re.finditer(r"^const (V\d\d): React\.FC", scenes_src, re.M)]

def which_scene(pos):
    cur = None
    for name, p in scene_at:
        if p < pos: cur = name
        else: break
    return "s" + cur[1:] if cur else None

G = geometry(sl)
_LERP = re.compile(r"lerp\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")

def endpoints(expr, loc, pos_block, depth=0):
    """칸 치수가 될 수 있는 값들. `lerp(a, b)` 는 **양 끝 둘 다** 봐야 한다 —
    한쪽만 보면 **움직이는 동안** 늘어나는 것을 놓친다. E01 s03 의 칸이 실제로
    `lerp(P.face.w, P.faceTight.w)` 라 한 끝만 보면 반만 재는 셈이 된다.
    `P.face.w` 같은 이름은 copy.ts 의 `S<NN>_POS` 블록에서 숫자를 꺼낸다."""
    e = expr.strip()
    if depth > 8: return []                               # 순환을 막는다
    if e in loc:                                          # 씬 안 `const faceW = …` 를 펴 준다
        return endpoints(loc[e], loc, pos_block, depth + 1)
    m = _LERP.search(e)
    if m and m.group(0) == e:
        return [x for side in (m.group(1), m.group(2))
                for x in endpoints(side, loc, pos_block, depth + 1)]
    v = _val(e, G, loc)
    if v is not None: return [v]
    mm = re.fullmatch(r"(?:\w+\.)?(\w+)\.(\w+)", e)       # P.face.w / face.w
    if mm and pos_block:
        blk = copy_block(copy_src, pos_block)
        f = re.search(rf"\b{mm.group(1)}:\s*\{{([^}}]*)\}}", blk)
        if f:
            n = re.search(rf"\b{mm.group(2)}:\s*(\d+)", f.group(1))
            if n: return [int(n.group(1))]
    return []

bad, unresolved, ok_n = [], [], 0
for u in uses:
    comp, asset, crop = u.group(1), u.group(2), u.group(3)
    sid = which_scene(u.start())
    cw = float(re.search(r"w:\s*([\d.]+)", crop).group(1)) if re.search(r"w:\s*([\d.]+)", crop) else 1.0
    ch = float(re.search(r"h:\s*([\d.]+)", crop).group(1)) if re.search(r"h:\s*([\d.]+)", crop) else 1.0
    img = REMOTION_DIR / "public" / sl / asset
    if not img.is_file():
        unresolved.append(f"{sid} {asset} — public/{sl}/ 에 파일이 없습니다"); continue
    with Image.open(img) as im: iw, ih = im.size
    want = (iw * cw) / (ih * ch)              # 화면에 오는 **잘라낸 조각**의 비

    body = scene_body(scenes_src, sid) if sid else ""
    loc = _locals_of(body) if body else {}
    pos_block = next((mm.group(0) for mm in re.finditer(r"S\d\d_POS", body)), None)
    ats = [m for m in _AT.finditer(scenes_src) if m.start() < u.start()]
    if not ats:
        unresolved.append(f"{sid} {asset} — 앞에 `<At w h>` 가 없습니다"); continue
    at = ats[-1]
    ws = endpoints(at.group(3), loc, pos_block)
    hs = endpoints(at.group(4), loc, pos_block)
    if not ws or not hs or len(ws) != len(hs):
        unresolved.append(f"{sid} {asset} — 칸 값을 못 풉니다: w={at.group(3).strip()} h={at.group(4).strip()}")
        continue
    for bw, bh in zip(ws, hs):
        got = bw / bh
        off = abs(got - want) / want
        line = (f"{sid} {comp} {asset} crop {cw:g}×{ch:g} → 조각 {iw*cw:.0f}×{ih*ch:.0f} (비 {want:.5f}) "
                f"· 칸 {bw}×{bh} (비 {got:.5f}) · 차 {off*100:.2f}%")
        if off > a.tol: bad.append(line)
        else: ok_n += 1

print(f"칸 비 검사 — 늘리는 부품 {len(FILL)}종({', '.join(FILL)}) · 호출 {len(uses)}곳 · "
      f"잰 칸 {ok_n + len(bad)}개 · 못 푼 것 {len(unresolved)}개 · 허용 차 {a.tol*100:g}%")
for u in unresolved:
    print(f"  ? {u}")
if bad:
    print(f"\n  ✕ 늘어난 칸 {len(bad)}개", file=sys.stderr)
    for b in bad: print(f"    {b}", file=sys.stderr)
    print("\n  **칸 비 = 화면에 오는 조각의 비** 여야 합니다. `objectFit: \"fill\"` 이라 남는 자리가 없어\n"
          "  둘이 다르면 그림이 그대로 늘어납니다 — 소재 **전체** 비를 쓰지 않았는지 보세요(E01 s03 이 그랬습니다).\n"
          "  칸은 연출(`scenes.tsx`)이, 부품은 미술(`parts.tsx`)이 정합니다.", file=sys.stderr)
    sys.exit(3)
if unresolved:
    print("  못 푼 칸이 있습니다 — **그 자리는 안 잰 것입니다.** 위 줄을 보고 값을 상수로 빼거나 알려 주세요.")
print("  ○ 잰 칸은 전부 소재 조각의 비와 맞습니다." if ok_n else "  잰 칸이 없습니다.")
