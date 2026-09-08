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
ap.add_argument("--set", default="", help="이 편의 기조 문법을 정하고 저장한다")
ap.add_argument("--except", dest="exc", default="",
                help="씬 단위 예외. 예) s00=stage,s09=workshop")
ap.add_argument("--verify", action="store_true",
                help="계획서의 카드가 실제 scenes.tsx 와 같은지 대조한다")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)

GRAMMARS_JSON = REMOTION_DIR / "src" / "knowhow" / "grammars.json"
if not GRAMMARS_JSON.exists(): die(f"문법 정의가 없습니다: {GRAMMARS_JSON}")
G = {k: v for k, v in jload(GRAMMARS_JSON).items() if k != "_"}

plan = ep / "script" / "visual_plan.md"
if not plan.exists(): die("script/visual_plan.md 없음 — 45단계를 먼저 돌리세요.")

# 계획서 표에서 씬별 카드를 뽑는다. 열 순서는 머리글로 찾는다(바뀌어도 따라간다).
# **머리글을 만난 그 표만 읽고 표가 끝나면 멈춘다.** 예전에는 인덱스를 그 뒤 모든 `|` 줄에
# 적용해서, 뒤에 오는 다른 표(씬 id 로 시작하는 박자 표·슬롯 표)가 카드를 덮어썼다 —
# 카드가 「글」·「8.8」 로 읽혔고 검사는 엉뚱한 이유로 종료코드 3 을 냈다.
used, i_scene, i_card, ncol = {}, None, None, 0
for line in plan.read_text(encoding="utf-8").splitlines():
    if not line.startswith("|"):
        i_scene = i_card = None       # 표가 끝났다. 다음 머리글을 다시 기다린다
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if "카드" in cells and "씬" in cells:
        i_scene, i_card, ncol = cells.index("씬"), cells.index("카드"), len(cells); continue
    if i_card is None or len(cells) != ncol: continue
    m = re.match(r"(s\d{2})", cells[i_scene].strip("*` "))
    card = cells[i_card].strip("*` ")
    if m and card:
        used[m.group(1)] = card
if not used: die("계획서에서 씬별 카드를 못 찾았습니다. 표에 '씬'과 '카드' 머리글이 있는지 확인하세요.")

shapes = sorted(set(used.values()))
print(f"씬 {len(used)}개 · 쓰는 카드 {len(shapes)}종: {', '.join(shapes)}\n")

gpath = ep / "script" / "grammar.json"
cur = jload(gpath) if gpath.exists() else {"base": "", "exceptions": {}}
if a.set or a.exc:
    if a.set:
        if a.set not in G: die(f"없는 문법: {a.set} (있는 것: {', '.join(G)})")
        cur["base"] = a.set
    if a.exc:
        exc = {}
        for pair in a.exc.split(","):
            sid, _, name = pair.partition("=")
            sid, name = sid.strip(), name.strip()
            if name not in G: die(f"없는 문법: {name}")
            if sid not in used: die(f"계획서에 없는 씬: {sid}")
            exc[sid] = name
        cur["exceptions"] = exc
    jdump(cur, gpath)
    print(f"기조 '{cur['base']}' · 예외 {len(cur['exceptions'])}개 → {gpath}\n")

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

cfg = jload(gpath); base = cfg["base"]; exc = cfg.get("exceptions", {})
if base not in G: die(f"script/grammar.json 의 base '{base}' 가 없는 문법입니다.")
print(f"이 편의 기조: {base} ({G[base]['label']}) — {G[base]['for']}")
if exc:
    by = {}
    for sid, name in sorted(exc.items()): by.setdefault(name, []).append(sid)
    for name, sids in by.items():
        print(f"  예외 {name} ({G[name]['label']}): {', '.join(sids)}")

# 씬마다 실제로 적용되는 문법으로 대조한다. 예외 씬은 기조가 아니라 그 문법이 담는다.
bad = []
for sid, card in sorted(used.items()):
    g = G[exc.get(sid, base)]
    if card not in g["carries"]:
        bad.append((sid, card, exc.get(sid, base)))
if bad:
    print("\n  ✕ 그 씬의 문법이 담을 수 없는 카드")
    for sid, card, name in bad:
        print(f"    {sid}  {card:9s} ← {name} 은 담지 못함 (담는 것: {', '.join(G[name]['carries'])})")
    print("    → 그 씬을 예외로 빼거나, 카드를 바꾸세요.")
    sys.exit(3)
print("\n  ○ 씬마다 그 문법이 카드를 담습니다.")

# 계획서는 만들고 나면 기록이 된다. 아무도 대조하지 않으면 조용히 거짓말이 된다.
# 실제로 그런 일이 있었다 — 계획서·grammar.json·구현이 s00 에서 셋 다 달랐다.
# scenes.tsx 의 각 씬 위에 붙인 `// card: <이름>` 이 구현 쪽의 답이다.
if a.verify:
    src = REMOTION_DIR / "src" / slug(ep) / "scenes.tsx"
    if not src.exists(): die(f"구현이 없습니다: {src}")
    # 선언 형태는 둘 다 받는다 — 씬을 switch 로 쓰던 때와 컴포넌트로 쓰는 지금.
    #   `// card: still` 다음 줄에 `case "s00":`   (옛 형태)
    #   `// s00 card: still`                       (씬 하나가 컴포넌트 하나일 때. id 를 선언이 들고 있다)
    _txt = src.read_text(encoding="utf-8")
    impl = {sid: card for card, sid in re.findall(r'//\s*card:\s*(\w+)\s*\n\s*case "(s\d\d)":', _txt)}
    impl.update({sid: card for sid, card in re.findall(r'//\s*(s\d\d)\s+card:\s*(\w+)', _txt)})
    print(f"\n계획서 ↔ 구현 대조 ({src.name})")
    miss = sorted(set(used) - set(impl))
    extra = sorted(set(impl) - set(used))
    diff = sorted((sid, used[sid], impl[sid]) for sid in set(used) & set(impl) if used[sid] != impl[sid])
    if miss:  print("  ✕ 구현에 카드 선언이 없는 씬: " + ", ".join(miss))
    if extra: print("  ✕ 계획서에 없는 씬이 구현에 있음: " + ", ".join(extra))
    for sid, plan_c, impl_c in diff:
        print(f"  ✕ {sid}  계획서 {plan_c} ≠ 구현 {impl_c}")
    if miss or extra or diff:
        print("    → 계획서를 실제에 맞추거나, 구현을 계획대로 바꾸세요.")
        sys.exit(4)
    print(f"  ○ {len(used)}개 씬이 계획서와 같습니다.")
print(f"  자막: {G[base]['caption']['layer']} · 아래 {G[base]['caption']['bottom']}px · "
      f"{G[base]['caption']['align']} · 안전영역 {G[base]['safeBottom']}px  (편 안에서 바뀌지 않음)")
