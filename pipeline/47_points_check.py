#!/usr/bin/env python3
"""내레이션이 화면을 **가리키는** 자리에서, 가리켜진 것이 맞는지 본다.

「이겁니다」·「오른쪽입니다」·「이렇게 바뀝니다」 처럼 **문장이 화면과 묶인 씬**이 있다.
그 자리에서 화면이 틀리면 내레이션이 거짓말을 한다. 나머지 씬은 화면이 틀려도 내레이션이 혼자 선다.

**이 검사가 필요한 이유는 「틀린 것이 빈 자리가 아니라 그럴듯한 다른 것」이기 때문이다**(작가).
s22 에서 좌우 두 칸에 **같은 클립이 두 번** 그려졌는데, v1 과 v2 가 같은 컷의 두 판본이라
**한 장만 나와도 「한 장짜리 씬」으로 읽혔다.** 담당 다섯이 다 통과시켰고 최종 편집자도 못 봤다.
켜진 화소도 · 대비도 · 겹침도 · 안전영역도 전부 통과한다 —
**「칸이 담고 있는 것이 무엇인가」를 아무도 안 물었다.**

가름은 **작가가 정하고 `script/points.json` 에 적는다.** 이 파일은 그것을 읽어 잴 뿐이다.
무엇이 떠야 하는지는 대본을 쓴 쪽만 안다.

사용:
    47_points_check.py <EP>                      글자·파일·셈만 본다
    47_points_check.py <EP> --master <mp4>       칸 그림까지 본다 (느리다)

종료코드: 0 통과 · 2 설정 오류 · 3 검사 실패
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import FPS, REMOTION_DIR, ep_dir  # noqa: E402


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ── 원본에서 조각을 떠 온다 ────────────────────────────────────────────────
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


def haystack(rule, sid, scenes_src, copy_src, ep):
    """규칙이 무엇을 대상으로 하는가. `where` 가 없으면 그 씬의 화면 코드 + 그 씬의 문구."""
    w = rule.get("where", "화면")
    if w == "화면":
        body = scene_body(scenes_src, sid)
        blk = copy_block(copy_src, "S" + sid[1:])
        return body + "\n" + blk, f"scenes.tsx 의 {sid} + copy.ts 의 S{sid[1:]}"
    if w.startswith("copy:"):
        name = w.split(":", 1)[1]
        return copy_block(copy_src, name), f"copy.ts 의 {name}"
    if w.startswith("파일:"):
        p = ep / w.split(":", 1)[1]
        if not p.exists():
            die(f"근거 파일이 없습니다: {p}\n  `where` 는 에피소드 폴더 기준 상대경로입니다")
        return p.read_text(encoding="utf-8"), str(p.relative_to(ep))
    die(f"`where` 를 모르겠습니다: {w}\n  쓸 수 있는 것: 화면 · copy:<이름> · 파일:<상대경로>")


# ── 화면 치수를 **코드에서 끌어온다** ─────────────────────────────────────
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


def _cut(big, rect, size):
    from PIL import Image
    import numpy as np
    x, y, w, h = rect
    return np.asarray(Image.fromarray(big[y:y + h, x:x + w]).resize(size)).astype(float)


def run_cellframe(rule, sid, master, scenes, slug, scenes_src, G):
    """**칸마다 어느 프레임이 들어 있나.** s09 처럼 한 소재의 여러 시각을 나란히 놓는 자리에서는
    「어느 파일인가」가 아니라 **「어느 프레임인가」**가 틀린다(미술).
    조각 클립을 배포에 넣어 대조하는 것은 오히려 나쁘다 — 같은 원본에서 잘린 것이라
    「제일 가까운 것」이 서로 뒤엉켜 **배수가 1 에 가까워지고 거짓 경고가 난다**(미술).
    **순위 1등으로 본다. 문턱이 없다.**"""
    import numpy as np
    from PIL import Image
    import io

    sc = [s for s in scenes if s["id"] == sid]
    if not sc:
        return False, f"{sid} 가 scenes_v2.json 에 없습니다"
    k = round(sc[0]["t_start"] * FPS) + round(rule["at"] * FPS)
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(0, k - 0.5) / FPS:.4f}", "-i", str(master),
         "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    if not out:
        return False, f"f{k} 를 못 떴습니다: {master}"
    big = np.asarray(Image.open(io.BytesIO(out)).convert("RGB")).astype(np.uint8)

    name = rule["asset"]
    src = REMOTION_DIR / "public" / slug / name
    if not src.exists():
        return False, f"소재가 없습니다: public/{slug}/{name}"
    step, size = rule.get("step", 1), (160, 90)
    frames = _asset_frames(src, step, size)
    if not frames:
        return False, f"소재에서 프레임을 못 떴습니다: {name}"
    sfps = _src_fps(src)
    times = [i * step / sfps for i in range(len(frames))]
    # **센 값과 디코딩한 장수를 댄다.** 다르면 디코더가 장을 만들었거나 버린 것이다 —
    # 그 차만큼 시각이 밀려 **없는 결함이 생긴다**(미술이 3장 때문에 대본을 고칠 뻔했다).
    counted = _counted_frames(src)
    frame_note = f"센 것 {counted}장" if counted is not None else "센 것 못 읽음"
    if counted is not None and step == 1 and counted != len(frames):
        frame_note += (f" ≠ 디코딩 {len(frames)}장  ← **{abs(counted - len(frames))}장 차이."
                       f" `-vsync 0` 쪽(={counted})이 맞습니다** — 컨테이너가 담고 있는 장수입니다")

    cells = rule["칸마다"]
    n = rule.get("나눔", len(cells))

    # **순위로 본다. 문턱이 없다**(미술). 여섯 칸의 그림을 **적힌 여섯 시각의 프레임**에만 대고,
    # 각 칸에서 1등이 제 짝이면 통과다. 이 하나로 **두 칸에 같은 프레임**과 **칸 순서 어긋남**이
    # 같이 잡힌다. 절대 시각으로 재지 않는 이유 — 스틸을 뽑을 때 `-ss` 가 반올림돼
    # **1~2프레임 어긋나는 것이 정상**인데, 그걸 문턱으로 만들면 그 수를 누가 정해야 한다.
    # (전수에서 가장 가까운 프레임은 **참고로만** 같이 찍는다.)
    pick = [min(range(len(frames)), key=lambda j: abs(times[j] - c["초"])) for c in cells]
    if len(set(pick)) != len(pick):
        return False, (f"{sid} — 적힌 시각 {[c['초'] for c in cells]} 중 둘이 **같은 프레임**을 가리킵니다"
                       f" (소재 {sfps:g}fps · 프레임 {len(frames)}장). 시각을 갈라 주세요")
    lines, bad = [], 0
    for ci, c in enumerate(cells):
        rc, err = rect_from_code(scenes_src, sid, name, None, G,
                                 needle=rule.get("칸 찾기"), n=n, idx=c["i"])
        if rc is None:
            return False, err
        cut = _cut(big, rc, size)
        d_all = [float(np.abs(f - cut).mean()) for f in frames]
        d_six = [d_all[j] for j in pick]
        win = int(np.argmin(d_six))
        order = sorted(range(len(d_six)), key=lambda z: d_six[z])
        margin = d_six[order[1]] / d_six[order[0]] if d_six[order[0]] > 0 else float("inf")
        ok = win == ci
        if not ok:
            bad += 1
        j = int(np.argmin(d_all))
        lines.append(f"칸 {c['i']} ({rc[0]},{rc[1]},{rc[2]},{rc[3]})  적힌 {c['초']:.2f}초 → "
                     f"여섯 중 1등 **{cells[win]['초']:.2f}초**(차 {d_six[win]:.2f} · 2등과 {margin:.2f}배)"
                     f" · 전수 1등 {times[j]:.2f}초"
                     + ("" if ok else "  ← **틀림**"))
    # **여섯이 여섯 「컷」에 드는가**(미술). 「1등이 제 시각」은 **「스틸이 제 이름과 맞다」까지**다 —
    # 같은 컷에서 두 장을 뽑아도 1등 검사는 통과한다. `[V]` 가 요구하는 것은 **서로 다른 컷**이다.
    # 컷 경계는 **이웃 프레임 화소차 상위 (칸수−1)개** — 칸이 여섯이면 컷도 여섯이라 경계가 다섯이다.
    # **이것도 순위다. 문턱이 없다.**
    if rule.get("서로 다른 컷"):
        dd = [float(np.abs(frames[i + 1] - frames[i]).mean()) for i in range(len(frames) - 1)]
        cutj = sorted(sorted(range(len(dd)), key=lambda i: -dd[i])[: len(cells) - 1])
        bounds = [0.0] + [(j + 1) * step / sfps for j in cutj] + [len(frames) * step / sfps]
        seg, room = [], []
        for c in cells:
            si = max(i for i in range(len(bounds) - 1) if bounds[i] <= c["초"])
            seg.append(si)
            room.append(min(c["초"] - bounds[si], bounds[si + 1] - c["초"]))
        okc = len(set(seg)) == len(seg) and seg == sorted(seg)
        if not okc:
            bad += 1
        lines.append(f"서로 다른 컷 — 경계 {['%.3f' % b for b in bounds[1:-1]]} · "
                     f"드는 샷 {seg} · 제일 좁은 여유 **{min(room):.3f}초**({min(room) * sfps:.1f}프레임)"
                     + ("" if okc else "  ← **둘 이상이 같은 컷이거나 순서가 어긋납니다**"))

    got = (f"{sid} 안 {rule['at']}초 (f{k}) · 칸 {len(cells)}개 / {n}등분 · "
           f"소재 {name} {len(frames)}프레임 · **{sfps:g}fps** · {frame_note} · **순위로 봄(문턱 없음)**"
           + "".join("\n            " + x for x in lines))
    return bad == 0, got





# ── 규칙 종류 ────────────────────────────────────────────────────────────
def run_static(rule, sid, scenes_src, copy_src, ep, slug):
    kind = rule["kind"]
    hay, where = haystack(rule, sid, scenes_src, copy_src, ep)

    if kind in ("글자 있음", "글자 없음"):
        need = rule["text"]
        found = need in hay
        ok = found if kind == "글자 있음" else not found
        got = f"{where} 에 「{need}」 {'있음' if found else '없음'}"
        return ok, got

    if kind == "몇 번":
        need, want = rule["text"], rule["count"]
        n = hay.count(need)
        return n == want, f"{where} 에 「{need}」 {n}번 (기대 {want}번)"

    if kind == "파일":
        name = rule["asset"]
        used = f'asset("{name}")' in hay
        p = REMOTION_DIR / "public" / slug / name
        exists = p.exists()
        got = f"{where} 에 `asset(\"{name}\")` {'있음' if used else '**없음**'} · " \
              f"public/{slug}/{name} {'있음' if exists else '**없음**'}"
        return used and exists, got

    if kind == "셈":
        arr = rule["array"]
        blk, where2 = haystack({"where": rule.get("where", "화면")}, sid, scenes_src, copy_src, ep)
        m = re.search(rf"{re.escape(arr)}\s*:\s*\[(.*?)\]", blk, re.S)
        if not m:
            return False, f"{where2} 에 `{arr}: [...]` 가 없습니다"
        n = len([x for x in re.findall(r'"(?:[^"\\]|\\.)*"', m.group(1))])
        return n == rule["count"], f"{where2} 의 `{arr}` 가 {n}개 (기대 {rule['count']}개)"

    if kind == "목록":
        # **셈만으로는 「넷 중 하나가 바뀐 것」을 못 잡는다**(작가) —
        # `[N]` 넷과 틀린 `[V]` 넷이 **둘 다 넷**이라 길이로는 갈리지 않았다.
        arr, want = rule["array"], rule["items"]
        blk, where2 = haystack({"where": rule.get("where", "화면")}, sid, scenes_src, copy_src, ep)
        m = re.search(rf"{re.escape(arr)}\s*:\s*\[(.*?)\]", blk, re.S)
        if not m:
            return False, f"{where2} 에 `{arr}: [...]` 가 없습니다"
        got = [x[1:-1] for x in re.findall(r'"(?:[^"\\]|\\.)*"', m.group(1))]
        if got == want:
            return True, f"{where2} 의 `{arr}` = {got} — 그대로입니다"
        more = [g for g in got if g not in want]
        less = [w for w in want if w not in got]
        why = []
        if more:
            why.append(f"더 있는 것 {more}")
        if less:
            why.append(f"없는 것 {less}")
        if not why:
            why.append("차례가 다릅니다")
        return False, f"{where2} 의 `{arr}` = {got} · 기대 {want} — " + " · ".join(why)

    die(f"`kind` 를 모르겠습니다: {kind}\n"
        f"  쓸 수 있는 것: 글자 있음 · 글자 없음 · 몇 번 · 파일 · 셈 · 목록 · 칸의 소재 · 칸의 프레임")


def _src_fps(path):
    """**소재의 초당 프레임.** 편의 FPS(30)로 셈하면 안 된다 —
    `c_reedit.mp4` 가 **24fps** 라 프레임 번호를 30 으로 나누니 시각이 0.8배로 나왔고,
    여섯 칸이 전부 「이르다」로 찍혔다. 0.8 = 24/30 이 그대로 보여 잡았다."""
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True).stdout.strip().rstrip(",")
    try:
        num, den = (float(x) for x in o.split("/"))
        return num / den if den else float(o)
    except ValueError:
        die(f"소재의 초당 프레임을 못 읽었습니다: {path} (ffprobe 가 {o!r} 를 줬습니다)")


def _counted_frames(path):
    """**컨테이너가 실제로 담고 있는 장수.** `-count_frames` 로 세어 본 값이다.

    **「도구가 준 것」과 「센 것」은 다르다**(미술). `c_reedit.mp4` 는 `r_frame_rate 24/1` 인데
    `avg_frame_rate` 가 23.745 라, 디코더가 24 로 맞추며 **3장을 복제해 189장**을 준다.
    그 189 로 재면 샷 길이가 밀려 **「최단 컷이 0.801 이 아니다」라는 없는 결함**이 나온다 —
    실제로 났고 대본을 고칠 뻔했다. `-vsync 0` 이면 186 으로 컨테이너와 맞는다."""
    o = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True).stdout.strip().rstrip(",")
    try:
        return int(o)
    except ValueError:
        return None


def _asset_frames(path, step, size):
    """소재에서 프레임을 훑어 작게 줄여 온다. 그림 한 장이 아니라 **전수**를 본다 —
    한 장만 보면 그 순간이 마침 비슷했을 뿐인지를 가릴 수 없다."""
    import numpy as np
    from PIL import Image
    import io
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", f"select='not(mod(n,{step}))',scale={size[0]}:{size[1]}",
         "-vsync", "0", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True).stdout
    frames, buf = [], out
    sig = b"\x89PNG\r\n\x1a\n"
    idx = [i for i in range(len(buf)) if buf.startswith(sig, i)]
    for i, st in enumerate(idx):
        en = idx[i + 1] if i + 1 < len(idx) else len(buf)
        frames.append(np.asarray(Image.open(io.BytesIO(buf[st:en])).convert("RGB")).astype(float))
    return frames


def run_frame(rule, sid, master, scenes, slug, scenes_src, G):
    """**칸이 담고 있는 것이 무엇인가.** 코드에 두 소재가 다 적혀 있어도 하나가 다른 하나를
    덮을 수 있다 — s22 가 그랬고, 정적 검사는 통과한다.
    칸에서 뜬 그림을 **기대한 소재와 헷갈릴 소재 전부**에 대 보고, 기대한 것이 제일 가까운지 본다."""
    import numpy as np
    from PIL import Image
    import io

    sc = [s for s in scenes if s["id"] == sid]
    if not sc:
        return False, f"{sid} 가 scenes_v2.json 에 없습니다"
    k = round(sc[0]["t_start"] * FPS) + round(rule["at"] * FPS)
    seek = max(0, k - 0.5) / FPS
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{seek:.4f}", "-i", str(master),
         "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True).stdout
    if not out:
        return False, f"f{k} 를 못 떴습니다: {master}"
    big = np.asarray(Image.open(io.BytesIO(out)).convert("RGB")).astype(np.uint8)
    want0 = rule["asset"]
    r = rule.get("rect", "코드")
    if r == "코드":
        # **좌표를 이 파일에 옮겨 적지 않는다.** 배치가 바뀌면 옮겨 적은 값만 낡는다(작가).
        rc, err = rect_from_code(scenes_src, sid, want0, rule.get("쪽"), G,
                                 needle=rule.get("칸 찾기"))
        if rc is None:
            return False, err
        x, y, w, h = rc
        src = f"코드에서 끌어옴{' · ' + rule['쪽'] + ' 쪽' if rule.get('쪽') else ''}"
    else:
        x, y, w, h = r
        src = "`points.json` 에 박힌 값"
    size = (160, 90)
    cut = np.asarray(Image.fromarray(big[y:y + h, x:x + w]).resize(size)).astype(float)

    want = want0
    cands = [want] + [c for c in rule.get("헷갈릴 것", []) if c != want]
    step = rule.get("step", 2)
    scores, missing = {}, []
    for name in cands:
        p = REMOTION_DIR / "public" / slug / name
        if not p.exists():
            # **기대한 소재가 없으면 실패**, 헷갈릴 것이 없으면 **건너뛰되 이름을 찍는다.**
            # 배포에 없는 것은 화면에 올 수 없다 — 다만 「몇 개를 대 봤나」가 안 보이면
            # 한 개만 대 보고 통과한 것과 구별이 안 된다.
            if name == want:
                return False, f"기대한 소재가 없습니다: public/{slug}/{name}"
            missing.append(name)
            continue
        fr = _asset_frames(p, step, size)
        if not fr:
            return False, f"소재에서 프레임을 못 떴습니다: {name}"
        scores[name] = (min(float(np.abs(f - cut).mean()) for f in fr), len(fr))
    cands = [c for c in cands if c in scores]

    order = sorted(scores, key=lambda n: scores[n][0])
    best = order[0]
    # **절대값이 아니라 배수로 본다.** 칸에 레터박스가 얼마나 드느냐에 따라 절대 차가 통째로 움직인다 —
    # 실측: 맞는 판 8.71/9.18, 틀린 판 79.70/96.41. 절대 문턱 8.0 을 걸었더니 **맞는 판이 떨어졌다.**
    # 배수(둘째 ÷ 첫째)는 그 영향을 안 받는다 — 맞는 판 2.54·1.64 · 틀린 판 0.99·1.00.
    ratio = (scores[order[1]][0] / scores[best][0]) if len(order) > 1 and scores[best][0] > 0 else float("inf")
    need = rule.get("배수", 1.3)
    ok = best == want and ratio >= need
    lines = " · ".join(f"{n} **{scores[n][0]:.2f}**({scores[n][1]}장)" if n == best
                       else f"{n} {scores[n][0]:.2f}({scores[n][1]}장)" for n in cands)
    tail = ""
    if missing:
        tail = (f"\n            **헷갈릴 것 {len(missing)}개는 배포에 없어 건너뜀** — "
                f"{' · '.join(missing)} (대 본 것 {len(cands)}개)")
    if len(cands) == 1:
        tail += ("\n            ⚠ **대 본 소재가 하나뿐이라 배수가 무한**입니다 — "
                 "「제일 가깝다」가 아무것도 안 가립니다")
    return ok, (f"{sid} 안 {rule['at']}초 (f{k}) 칸 ({x},{y},{w},{h}) [{src}] → 가장 가까운 소재 "
                f"**{best}** · 기대 {want} · 둘째와 **{ratio:.2f}배** (문턱 {need}배)"
                f"\n            {lines}{tail}")


# ── ──────────────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser(description="내레이션이 가리키는 자리에서 가리켜진 것이 맞는지 본다")
ap.add_argument("ep")
ap.add_argument("--master", help="칸 그림까지 보려면 마스터 mp4 를 준다 (없으면 그 규칙은 건너뛴다)")
a = ap.parse_args()

ep = ep_dir(a.ep)
slug = ep.name.split("_")[0].lower()
rules_p = ep / "script" / "points.json"
if not rules_p.exists():
    die(f"가름표가 없습니다: {rules_p}\n"
        f"  이 파일은 **작가가 씁니다** — 어느 씬에서 무엇이 떠야 하는지는 대본을 쓴 쪽만 압니다")

doc = json.loads(rules_p.read_text(encoding="utf-8"))
points = doc["points"] if isinstance(doc, dict) else doc

src_dir = REMOTION_DIR / "src" / slug
scenes_f, copy_f = src_dir / "scenes.tsx", src_dir / "copy.ts"
for f in (scenes_f, copy_f):
    if not f.exists():
        die(f"화면 코드가 없습니다: {f}")
scenes_src = scenes_f.read_text(encoding="utf-8")
copy_src = copy_f.read_text(encoding="utf-8")

G = geometry(slug)
print(f"화면: 문법 {G['문법']} · 프리셋 {G['프리셋']} · 안쪽 **{G['W']}×{G['H']}** "
      f"(edge {G['edge']} · gap {G['gap']} · safeBottom {G['safeBottom']}) — **전부 코드에서 읽었습니다**")
print()

scenes_json = ep / "script" / "scenes_v2.json"
scenes = []
if scenes_json.exists():
    d = json.loads(scenes_json.read_text(encoding="utf-8"))
    scenes = d["scenes"] if isinstance(d, dict) else d

master = pathlib.Path(a.master) if a.master else None
if master and not master.exists():
    die(f"마스터가 없습니다: {master}")

n_ok = n_bad = n_skip = 0
bad = []
for p in points:
    sid = p["scene"]
    print(f"{sid}  {p.get('말', '')}")
    for rule in p["rules"]:
        if rule["kind"] in ("칸의 소재", "칸의 프레임"):
            if not master:
                n_skip += 1
                print(f"      건너뜀 — `--master` 를 줘야 봅니다: {rule.get('왜', '')}")
                continue
            fn = run_cellframe if rule["kind"] == "칸의 프레임" else run_frame
            ok, got = fn(rule, sid, master, scenes, slug, scenes_src, G)
        else:
            ok, got = run_static(rule, sid, scenes_src, copy_src, ep, slug)
        mark = "통과" if ok else "**실패**"
        print(f"      {mark}  {got}")
        if rule.get("왜"):
            print(f"            {rule['왜']}")
        if ok:
            n_ok += 1
        else:
            n_bad += 1
            bad.append(f"{sid} — {got}")

tot = n_ok + n_bad + n_skip
print()
print(f"가리키는 자리 **{len(points)}곳** · 규칙 {tot}개 — "
      f"통과 {n_ok} · 실패 {n_bad} · 건너뜀 {n_skip}")
if n_skip:
    print("  건너뛴 것은 `--master <mp4>` 를 주면 봅니다. **정적으로는 못 보는 종류입니다.**")
if n_bad:
    print()
    print("실패한 것:")
    for b in bad:
        print(f"  · {b}")
    sys.exit(3)
