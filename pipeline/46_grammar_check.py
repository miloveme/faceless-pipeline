#!/usr/bin/env python3
"""이 편이 고른 화면 문법이 계획서의 카드를 전부 담을 수 있는지 본다.

문법은 보기 좋아서 고르는 게 아니라 그 편의 내용 모양이 정한다.
표가 넷인 편에 상자 없는 문법을 쓰면 표가 뭉개진다 — 그건 렌더해 봐야 아는 게 아니라
계획서만 보고도 알 수 있다. 그걸 여기서 잡는다.

읽는 것: script/visual_plan.md 의 표(카드 열), script/grammar.json, grammars.json
사용: 46_grammar_check.py <EP> [--set panel|stage|workshop]
"""
import argparse, json
from common import *

ap = argparse.ArgumentParser(); ap.add_argument("ep")
ap.add_argument("--set", default="", help="이 편의 문법을 정하고 저장한다")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)

GRAMMARS_JSON = REMOTION_DIR / "src" / "knowhow" / "grammars.json"
if not GRAMMARS_JSON.exists(): die(f"문법 정의가 없습니다: {GRAMMARS_JSON}")
G = {k: v for k, v in jload(GRAMMARS_JSON).items() if k != "_"}

plan = ep / "script" / "visual_plan.md"
if not plan.exists(): die("script/visual_plan.md 없음 — 45단계를 먼저 돌리세요.")

# 계획서 표에서 씬별 카드를 뽑는다. 열 순서는 머리글로 찾는다(바뀌어도 따라간다).
used, i_scene, i_card = {}, None, None
for line in plan.read_text(encoding="utf-8").splitlines():
    if not line.startswith("|"): continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if "카드" in cells and "씬" in cells:
        i_scene, i_card = cells.index("씬"), cells.index("카드"); continue
    if i_card is None or len(cells) <= i_card: continue
    m = re.match(r"(s\d{2})", cells[i_scene])
    card = cells[i_card].strip("*` ")
    if m and card:
        used[m.group(1)] = card
if not used: die("계획서에서 씬별 카드를 못 찾았습니다. 표에 '씬'과 '카드' 머리글이 있는지 확인하세요.")

shapes = sorted(set(used.values()))
print(f"씬 {len(used)}개 · 쓰는 카드 {len(shapes)}종: {', '.join(shapes)}\n")

gpath = ep / "script" / "grammar.json"
if a.set:
    if a.set not in G: die(f"없는 문법: {a.set} (있는 것: {', '.join(G)})")
    jdump({"base": a.set, "exceptions": {}}, gpath)
    print(f"이 편의 문법을 '{a.set}' 로 정했습니다 → {gpath}\n")

print("문법별로 담을 수 있나")
fits = []
for name, g in G.items():
    miss = sorted({c for c in shapes if c not in g["carries"]})
    mark = "○" if not miss else "✕"
    note = "전부 담김" if not miss else "못 담음: " + ", ".join(miss)
    print(f"  {mark} {name:9s} {g['label']:5s} — {note}")
    if not miss: fits.append(name)

print()
if not gpath.exists():
    print("이 편의 문법이 아직 정해지지 않았습니다.")
    print("  " + (f"쓸 수 있는 것: {', '.join(fits)}" if fits else "지금 카드 구성을 다 담는 문법이 없습니다."))
    print("  --set 으로 정하세요. 예) 46_grammar_check.py <EP> --set panel")
    sys.exit(2)

cfg = jload(gpath); base = cfg["base"]
if base not in G: die(f"script/grammar.json 의 base '{base}' 가 없는 문법입니다.")
miss = sorted({c for c in shapes if c not in G[base]["carries"]})
print(f"이 편의 문법: {base} ({G[base]['label']}) — {G[base]['for']}")
if miss:
    bad = sorted({s for s, c in used.items() if c in miss})
    print(f"  ✕ 담을 수 없는 카드: {', '.join(miss)}")
    print(f"    해당 씬: {', '.join(bad)}")
    print(f"    → 문법을 바꾸거나({', '.join(fits) if fits else '대안 없음'}), 그 씬의 카드를 바꾸세요.")
    sys.exit(3)
print("  ○ 계획서의 카드를 전부 담습니다.")
print(f"  자막: {G[base]['caption']['layer']} · 아래 {G[base]['caption']['bottom']}px · "
      f"{G[base]['caption']['align']} · 안전영역 {G[base]['safeBottom']}px  (편 안에서 바뀌지 않음)")
