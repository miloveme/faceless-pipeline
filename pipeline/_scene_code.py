#!/usr/bin/env python3
"""씬 코드(`scenes.tsx`·`copy.ts`)에서 **자리와 값을 읽어 오는** 공용 층.

`47_points_check.py` 가 쓰던 것을 여기로 옮겼다. `63_aspect_check.py` 가 같은 것을 봐야 하는데,
**옮겨 적으면 둘이 갈린다** — 배치가 바뀔 때 한쪽만 낡고 아무도 안 잰다.
그 경고가 이미 `geometry()` 독스트링에 있었다(작가가 짚은 자리).

**여기 있는 것은 읽기뿐이다.** 판정은 부르는 쪽이 한다.
"""
import json, re, sys
from common import REMOTION_DIR


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def scene_body(scenes_src: str, sid: str) -> str:
    """`const Vnn: React.FC` 부터 다음 `const Vnn` 앞까지. **`S03_POS` 같은 것에 안 걸리게**
    `^const V\\d\\d: React.FC` 로만 자른다 — 전에 `^export const S(\\d\\d)` 로 잘라서
    `S03_POS`·`S05_BODY` 가 씬으로 세어졌다."""
    n = sid[1:]
    starts = [(m.group(1), m.start()) for m in re.finditer(r"^const (V\d\d): React\.FC", scenes_src, re.M)]
    for i, (name, pos) in enumerate(starts):
        if name[1:] != n:
            continue
        end = starts[i + 1][1] if i + 1 < len(starts) else len(scenes_src)
        return scenes_src[pos:end]
    return ""


def copy_block(copy_src: str, name: str) -> str:
    """`export const NAME = {` 부터 다음 `export const` 앞까지."""
    m = re.search(rf"^export const {re.escape(name)}\b", copy_src, re.M)
    if not m:
        return ""
    nxt = re.search(r"^export const ", copy_src[m.end():], re.M)
    return copy_src[m.start(): m.end() + (nxt.start() if nxt else len(copy_src))]


def geometry(slug):
    """`W`·`H`·`T.gap`·`T.edge` 를 실제 파일에서 읽는다. **옮겨 적지 않는다** —
    옮겨 적으면 배치가 바뀔 때 이 파일만 낡고 아무도 안 잰다(작가가 짚은 자리)."""
    th = (REMOTION_DIR / "src" / "knowhow" / "theme.ts").read_text(encoding="utf-8")
    m = re.search(r"\.\.\.PRESETS\.(\w+)", th)
    if not m:
        die("theme.ts 에서 쓰는 프리셋을 못 찾았습니다 (`...PRESETS.<이름>`)")
    preset = m.group(1)
    blk = re.search(rf"^  {preset}: \{{(.*?)^  \}},", th, re.S | re.M)
    if not blk:
        die(f"theme.ts 에 프리셋 `{preset}` 블록이 없습니다")
    def tok(name):
        mm = re.search(rf"\b{name}: (\d+)", blk.group(1))
        if not mm:
            die(f"theme.ts 의 `{preset}` 에 `{name}` 이 없습니다")
        return int(mm.group(1))
    edge, gap = tok("edge"), tok("gap")

    parts = (REMOTION_DIR / "src" / slug / "parts.tsx").read_text(encoding="utf-8")
    mg = re.search(r'panelInner\("(\w+)"\)', parts)
    if not mg:
        die(f"{slug}/parts.tsx 에서 `panelInner(\"<문법>\")` 을 못 찾았습니다")
    gname = mg.group(1)
    gj = json.loads((REMOTION_DIR / "src" / "knowhow" / "grammars.json").read_text(encoding="utf-8"))
    if gname not in gj:
        die(f"grammars.json 에 문법 `{gname}` 이 없습니다")
    g = gj[gname]
    if g["contain"]["kind"] != "none":
        die(f"문법 `{gname}` 의 담기가 `{g['contain']['kind']}` 입니다 — "
            f"이 검사는 아직 `none`(상자 없음)만 셈합니다. Container.tsx 의 `insetOf` 와 맞춰 주세요")
    safe = g["safeBottom"]
    W = 1920 - 2 * edge
    H = 1080 - edge - safe
    return {"W": W, "H": H, "edge": edge, "gap": gap, "문법": gname, "safeBottom": safe,
            "프리셋": preset}


_NUM = re.compile(r"^[\d\s+\-*/().]+$")
_CONST = re.compile(r"^\s*const\s+(.+?);\s*$", re.M)


def _locals_of(body):
    """씬 안의 `const a = …, b = …;` 를 이름→식으로 모은다. **푸는 것은 `_val` 이 한다** —
    여기서 미리 계산하면 `W`·`T.gap` 이 안 풀린 채로 남아 조용히 틀린다."""
    out = {}
    for m in _CONST.finditer(body):
        line = m.group(1)
        if "=>" in line or "{" in line:                          # 함수·객체는 안 본다
            continue
        for part in re.split(r",(?![^()]*\))", line):
            mm = re.match(r"\s*(\w+)\s*=\s*(.+)$", part)
            if mm:
                out.setdefault(mm.group(1), mm.group(2).strip())
    return out


def _val(expr, G, loc=None):
    """`{...}` 안의 식을 푼다. **아는 이름만** 푼다 — 모르면 `None` 을 준다.
    조용히 0 이 되면 안 되므로 부르는 쪽이 「`rect` 를 직접 주세요」로 죽는다.
    씬 안에서 `const` 로 만든 이름은 그 식을 대신 넣어 푼다(**여덟 번까지만** — 순환을 막는다)."""
    e = expr.strip()
    loc = loc or {}
    for _ in range(8):
        before = e
        for k, v in (("W", G["W"]), ("H", G["H"]), ("T.gap", G["gap"]), ("T.edge", G["edge"])):
            e = re.sub(rf"(?<![\w.]){re.escape(k)}(?![\w])", str(v), e)
        e = e.replace("Math.round(", "round(")
        for k, v in loc.items():
            if k in ("W", "H"):
                continue
            e = re.sub(rf"(?<![\w.]){re.escape(k)}(?![\w])", f"({v})", e)
        if e == before:
            break
    e2 = e.replace("round(", "")                                  # 검사용으로만 벗긴다
    if not _NUM.match(e2.replace(")", ")")):
        return None
    try:
        return int(round(eval(e, {"__builtins__": {}, "round": round})))   # noqa: S307
    except Exception:
        return None


_AT = re.compile(r"<At\s+x=\{([^}]*)\}\s*y=\{([^}]*)\}\s*w=\{([^}]*)\}\s*h=\{([^}]*)\}", re.S)


def rect_from_code(scenes_src, sid, asset_name, side, G, needle=None, n=1, idx=0):
    """`asset("이름")` 을 감싸는 **가장 가까운 앞쪽 `<At x y w h>`** 를 찾아 화면 절대 좌표로 준다.

    `쪽` 이 있으면 `Duo` 처럼 `T.gap` 으로 반씩 나눈 한 쪽을,
    `나눔` 이 있으면 `T.gap` 을 사이에 두고 **n 등분한 idx 번째 칸**을 준다.
    `칸 찾기` 를 주면 그 문자열로 자리를 찾는다 — 소재 이름이 템플릿 리터럴이라
    `asset("…")` 로는 안 잡히는 자리가 있다(s09 썸네일이 `` asset(`c_reedit_${t}.png`) `` 다)."""
    body = scene_body(scenes_src, sid)
    if not body:
        return None, f"{sid} 의 화면 코드를 못 찾았습니다"
    key = needle or f'asset("{asset_name}")'
    i = body.find(key)
    if i < 0:
        return None, f"{sid} 에 `{key}` 가 없습니다"
    ats = [m for m in _AT.finditer(body) if m.start() < i]
    if not ats:
        return None, f"{sid} 의 `{asset_name}` 앞에 `<At x y w h>` 가 없습니다 — `rect` 를 직접 주세요"
    m = ats[-1]
    loc = _locals_of(body)
    vals = [_val(g, G, loc) for g in m.groups()]
    if any(v is None for v in vals):
        return None, (f"{sid} 의 `<At>` 값을 못 풉니다: "
                      f"x={m.group(1).strip()} y={m.group(2).strip()} "
                      f"w={m.group(3).strip()} h={m.group(4).strip()} — `rect` 를 직접 주세요")
    x, y, w, h = vals
    if side:
        half = (w - G["gap"]) // 2
        x = x + (half + G["gap"] if side == "우" else 0)
        w = half
    if n > 1:
        cw = (w - (n - 1) * G["gap"]) / n
        x = round(x + idx * (cw + G["gap"]))
        w = round(cw)
    return [x + G["edge"], y + G["edge"], w, h], None

