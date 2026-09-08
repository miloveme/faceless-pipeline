#!/usr/bin/env python3
"""**목록이 지금 대본을 가리키는가.** 씬 번호를 적어 둔 문서·설정을 `scenes_v1.json` 과 댄다.

씬은 대본을 고칠 때마다 늘고 줄고 밀린다. 그때 **씬 번호를 적어 둔 목록은 안 따라온다** —
만들 때는 맞았고 그 뒤에 아무도 안 본다. 2026-09-09 E01 에서 하루에 **넷이 다 낡았다**:
대조표 · 챕터 · 소재표 · 가름표. **넷 다 사람이 열어서야 나왔다.**

**방향이 둘이다. 둘 다 봐야 한다.**
  목록 → 대본   적힌 씬이 지금 있는가            (없어진 씬을 가리키는 줄)
  대본 → 목록   지금 씬이 목록에 한 줄이라도 있는가  (대조를 한 번도 안 받은 씬)
앞엣것만 보면 **새로 생긴 씬이 조용히 빠진다** — 그것이 s15 를 놓친 자리다(작가).

무엇을 댈지는 **그 파일을 쓰는 사람이 정한다.** 여기 목록은 작가가 준 것이고,
새 파일이 늘면 `TARGETS` 에 한 줄 더한다.

사용: 06_lists_check.py <EP>
종료코드: 0 통과 · 2 설정 오류 · 3 검사 실패
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ep_dir  # noqa: E402

SID = re.compile(r"\bs\d\d\b")

# (파일, 무엇인가, 양방향인가, 어디서 뽑나)
#   **양방향**이면 「대본의 모든 씬이 목록에 있는가」도 본다.
#   **어디서 뽑나** 가 없으면 파일 전체에서 `sNN` 을 뽑는다. `{"칸": ..., "절": ...}` 이면
#   그 절의 그 칸에서만 뽑는다.
#
# **파일 전체에서 뽑으면 산문이 검사를 초록으로 만든다**(작가). `SOURCES.md` 에
# 「표에 없는 씬은 화면이 소재가 아니라 글자·도식이다 — s00 · s01 · …」 한 줄이 있어서
# 표의 15종이 **31종으로 보였다.** 그 줄 하나 때문에 **소재표에서 열여섯 줄이 통째로
# 사라져도 안 걸린다.** 설명하려고 쓴 문장이 검사의 눈을 가린 것이다.
TARGETS = [
    ("script/points.json", "가리키는 자리 가름표(작가) — **한 방향**. "
     "내레이션이 화면을 가리키는 자리만 적는 파일이라 31씬이 다 있을 이유가 없다",
     False, {"열쇠": "scene"}),
    ("source/SOURCES.md", "주 소재표(작가) — **한 방향**. 소재가 없는 씬이 있다 "
     "(글자·도식으로 서는 씬들). 「전부 있어야 한다」로 두면 없는 소재를 만들게 된다",
     False, {"칸": "씬"}),
    ("source/EVIDENCE.md", "대조표(작가) — **양방향**. 여기만 31씬이 다 있어야 한다: "
     "**주장이 있으면 근거가 있어야** 하고, 근거가 없는 씬은 「없음」을 적는다",
     True, {"칸": "씬", "절": r"^##\s*3\."}),
]


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _cells(line):
    """마크다운 표 한 줄을 칸으로 가른다. 앞뒤의 빈 칸은 버린다."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def ids_in(path: pathlib.Path, where=None):
    """`sNN` 을 뽑는다. **줄 번호를 같이 들고 온다** —
    「셋 있다」만 찍으면 어느 줄인지를 사람이 다시 찾아야 한다.

    `where` 가 있으면 **그 절의 그 칸에서만** 뽑는다. 없으면 파일 전체다."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out, rows = {}, 0
    if not where:
        for n, line in enumerate(lines, 1):
            for m in SID.finditer(line):
                out.setdefault(m.group(0), []).append(n)
        return out, len(lines), "파일 전체"

    if where.get("열쇠"):
        # JSON 은 **그 열쇠의 값만** 본다. 산문(`왜`)에 씬 이름이 들어 있어도 안 센다 —
        # 마크다운의 「산문이 검사를 초록으로 만든다」와 같은 자리다.
        key = where["열쇠"]
        doc = json.loads("\n".join(lines))
        seen = 0

        def walk(o):
            nonlocal seen
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == key and isinstance(v, str):
                        seen += 1
                        for m in SID.finditer(v):
                            out.setdefault(m.group(0), []).append(0)
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(doc)
        return out, seen, f"열쇠 `{key}` 의 값"

    sec = re.compile(where["절"]) if where.get("절") else None
    col_name, in_sec, col = where["칸"], sec is None, None
    for n, line in enumerate(lines, 1):
        if line.startswith("#"):
            if sec:
                in_sec = bool(sec.match(line))
            col = None                                   # 절이 바뀌면 표도 끝난다
            continue
        if not in_sec:
            continue
        if not line.lstrip().startswith("|"):
            col = None                                   # 표가 끝났다
            continue
        cs = _cells(line)
        if col is None:
            if col_name in cs:
                col = cs.index(col_name)                 # 머리줄을 찾았다
            continue
        if set("".join(cs)) <= set("-: "):
            continue                                     # `|---|` 줄
        if col >= len(cs):
            continue
        rows += 1
        for m in SID.finditer(cs[col]):
            out.setdefault(m.group(0), []).append(n)
    if col_name not in [c for line in lines if line.lstrip().startswith("|") for c in _cells(line)]:
        die(f"{path.name} 에 「{col_name}」 칸이 있는 표를 못 찾았습니다 — "
            f"칸 이름이 바뀌었으면 `TARGETS` 를 고쳐 주세요")
    return out, rows, f"「{col_name}」 칸" + (f" · 절 {where['절']}" if where.get("절") else "")


# 표와 산문이 대본을 **딱 나누는가**. (파일, 표에서 뽑는 법, 산문 줄을 찾는 정규식, 무엇인가)
#
# `SOURCES.md` 는 표에 **소재가 있는 씬**만 적고, 표 아래 한 줄이 **없는 씬 열여섯**을 센다.
# **그 줄이 낡는 경로가 뻔하다**(작가) — 소재가 없던 씬에 소재가 붙으면 표에 한 줄이 늘고
# 산문에서 하나를 빼야 하는데, **표만 고치고 산문을 안 고친다.**
# 셈이 닫히면 **산문이 스스로 자기가 낡았다고 말한다.**
COMPLEMENTS = [
    ("source/SOURCES.md", {"칸": "씬"}, r"표에 없는 씬은",
     "주 소재표 — **표(소재 있음) + 산문(소재 없음) = 대본 전부**, 겹침 0(작가)"),
]

ep = ep_dir(sys.argv[1] if len(sys.argv) > 1 else die("사용: 06_lists_check.py <EP>"))
sc_p = ep / "script" / "scenes_v1.json"
if not sc_p.exists():
    die(f"scenes_v1.json 이 없습니다: {sc_p}\n  먼저 05_script_to_scenes.py 를 돌리세요")
d = json.loads(sc_p.read_text(encoding="utf-8"))
SCENES = [s["id"] for s in (d["scenes"] if isinstance(d, dict) else d)]
KNOWN = set(SCENES)
print(f"대본: `scenes_v1.json` 의 씬 **{len(SCENES)}개** ({SCENES[0]}~{SCENES[-1]})")
print()

n_bad = 0
for rel, what, both, where in TARGETS:
    p = ep / rel
    if not p.exists():
        print(f"{rel:26s} 없음 — 건너뜁니다 ({what})")
        continue
    found, rows, scope = ids_in(p, where)
    ghost = {k: v for k, v in found.items() if k not in KNOWN}
    print(f"{rel:26s} {what}")
    print(f"{'':26s}   **{scope}**에서 뽑음 · 본 줄 {rows}개 · "
          f"씬 번호 **{len(found)}종** · {sum(len(v) for v in found.values())}번 나옴")
    if ghost:
        n_bad += 1
        print(f"{'':26s}   ← **없는 씬을 가리키는 것 {len(ghost)}종**: "
              + " · ".join(
                  f"{k}({'·'.join(str(x) for x in v)}행)" if v and v[0] else k
                  for k, v in sorted(ghost.items())))
    else:
        print(f"{'':26s}   없는 씬을 가리키는 것 **0종** (본 씬 번호 {len(found)}종)")
    if both:
        miss = [s for s in SCENES if s not in found]
        if miss:
            n_bad += 1
            print(f"{'':26s}   ← **목록에 한 줄도 없는 씬 {len(miss)}개**: {' '.join(miss)}")
        else:
            print(f"{'':26s}   목록에 없는 씬 **0개** (대본 {len(SCENES)}개를 다 봤습니다)")

# ── 표 + 산문이 대본을 딱 나누는가 ────────────────────────────────────────
for rel, where, prose_re, what in COMPLEMENTS:
    p = ep / rel
    if not p.exists():
        continue
    tbl, _, scope = ids_in(p, where)
    _pat = re.compile(prose_re)
    # **줄이 접혀 있을 수 있다.** 마크다운은 빈 줄까지가 한 문단이라, 표시 줄부터
    # **빈 줄이 나올 때까지** 이어 읽는다. 접힌 것을 안 보면 열여섯이 여덟으로 세어진다.
    prose, prose_ln, prose_to = {}, None, None
    _lines = p.read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(_lines, 1):
        if _pat.search(line):
            prose_ln = n
            for k in range(n - 1, len(_lines)):
                if k > n - 1 and not _lines[k].strip():
                    break
                prose_to = k + 1
                for m in SID.finditer(_lines[k]):
                    prose[m.group(0)] = k + 1
            break
    print()
    print(f"{rel:26s} {what}")
    if prose_ln is None:
        n_bad += 1
        print(f"{'':26s}   ← **산문 줄을 못 찾았습니다** (`{prose_re}`). "
              f"줄이 없어졌거나 문구가 바뀌었습니다")
        continue
    both = sorted(set(tbl) & set(prose))
    miss = [x for x in SCENES if x not in tbl and x not in prose]
    ghost = sorted((set(tbl) | set(prose)) - KNOWN)
    _pl = f"{prose_ln}행" if prose_to == prose_ln else f"{prose_ln}~{prose_to}행"
    print(f"{'':26s}   표({scope}) **{len(tbl)}종** + 산문({_pl}) **{len(prose)}종** "
          f"= {len(set(tbl) | set(prose))}종 / 대본 {len(SCENES)}개")
    ok = True
    if both:
        ok = False
        print(f"{'':26s}   ← **양쪽에 있는 것 {len(both)}개**: {' '.join(both)} "
              f"(표는 소재 있음 · 산문은 소재 없음이라 겹칠 수 없습니다)")
    if miss:
        ok = False
        print(f"{'':26s}   ← **어느 쪽에도 없는 씬 {len(miss)}개**: {' '.join(miss)}")
    if ghost:
        ok = False
        print(f"{'':26s}   ← **없는 씬 {len(ghost)}개**: {' '.join(ghost)}")
    if ok:
        print(f"{'':26s}   겹침 **0** · 빠짐 **0** — 셈이 닫힙니다")
    else:
        n_bad += 1

print()
print(f"목록 **{len(TARGETS)}개** + 짝 검사 **{len(COMPLEMENTS)}개** 중 어긋난 검사 **{n_bad}건**")
if n_bad:
    print("  **목록이 지금 대본을 안 가리킵니다.** 그 파일을 쓴 사람에게 줄 번호와 함께 넘기세요 —")
    print("  여기서 고치지 않습니다. 무엇이 맞는지는 그 파일의 주인이 압니다.")
    sys.exit(3)
