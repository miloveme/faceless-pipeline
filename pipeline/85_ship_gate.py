#!/usr/bin/env python3
"""**사용자에게 보내기 전에 서는 관문.** 마스터 하나를 받아 셋을 막는다.

**이 관문은 담당이 아니라 총괄을 막는다.** 2026-09-09 E01 에서 난 둘이 다 총괄 자리였다 —
최종 편집자를 다섯 판 미룬 것, 사용자 요청을 표 없이 기억으로 관리한 것.
**마음먹으면 건너뛸 수 있는 것은 시스템이 아니다**(총괄).

```
막는 것 셋
  ㄱ  요청 대장에 **「재서 확인됨」이 아닌 항목**이 있다
  ㄴ  확인은 됐는데 그 **지문이 이 마스터와 다르다**   ← 「어느 판본의」가 오늘 세 번 났다
  ㄷ  **최종 편집자 판정이 이 지문에 대해 없다**
통과해도 찍는 것
  **분모** — 「대장 17건 중 17건 확인 · 편집자 판정 있음(지문 …)」
  **분모 없는 통과가 오늘 여러 번 속였다.**  빠진 것은 **이름으로** 찍는다
```

**「사용자가 원한 뜻인가」는 여기서 판정하지 않는다.** 그건 사람이 본다(총괄).
**관문이 묻는 것은 「봤는가 · 어느 판본에서 봤는가」까지다** —
잣대가 사용자 결정을 되돌릴 뻔한 일이 오늘 있었고, 여기서 그러면 훨씬 나쁘다.

**어디까지 됐나** (2026-09-09 · 반쯤 만든 검사가 「다 된 것」으로 읽히지 않게 적는다)
```
됐다   ㄱ·ㄴ·ㄷ 셋 다 돌고 **막는다.**  E01 v11 로 시험해 종료코드 3 을 확인했다
       빠진 것을 **이름·담당·자리**로 찍고, 통과해도 **분모**를 찍는다
안 됐다  **한 번도 「통과」로 끝난 적이 없다.**  E01 에서 대장이 아직 「들어감 12」이고
       편집자 판정이 비어 있어 **통과 경로를 실제로 밟아 보지 못했다**
       → 처음 통과할 때 **마지막 두 줄이 뜻대로 찍히는지** 눈으로 보라
안 한다  이 관문을 **`60` 이나 `65` 가 자동으로 부르지 않는다.**  올리기 직전에 사람이 부른다 —
       굽는 때마다 부르면 늘 막힌다(「들어감」은 마스터가 있어야 「재서 확인됨」이 된다)
```

사용: 85_ship_gate.py <EP> <마스터.mp4>
종료코드: 0 통과 · 2 설정 오류 · 3 **막힘**
"""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ep_dir  # noqa: E402


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


if len(sys.argv) < 3:
    die("사용: 85_ship_gate.py <EP> <마스터.mp4>")
ep = ep_dir(sys.argv[1])
master = pathlib.Path(sys.argv[2])
if not master.exists():
    die(f"마스터가 없습니다: {master}")
FP = subprocess.run(["shasum", "-a", "1", str(master)], capture_output=True, text=True).stdout[:8]

req_p = ep / "script" / "requests.json"
ver_p = ep / "script" / "editor_verdicts.json"
if not req_p.exists():
    die(f"요청 대장이 없습니다: {req_p}  — `07_requests_check.py` 를 먼저 보세요")
items = json.loads(req_p.read_text(encoding="utf-8"))["요청"]

print(f"관문: {master.name} · 지문 **{FP}**")
print()

blocked = []

# ── ㄱ·ㄴ 요청 대장 ─────────────────────────────────────────────────────────
not_done = [(i, x) for i, x in enumerate(items, 1) if x.get("상태") != "재서 확인됨"]
stale = [(i, x) for i, x in enumerate(items, 1)
         if x.get("상태") == "재서 확인됨" and x.get("판본") != FP]
print(f"ㄱ 요청 대장 — **{len(items) - len(not_done)}/{len(items)}건**이 「재서 확인됨」")
for i, x in not_done:
    print(f"    ← {i}번 **{x.get('상태')}**  {x['요청'][:60]}{'…' if len(x['요청']) > 60 else ''}")
    print(f"       담당 {x.get('담당', '—')} · 자리 {' · '.join(x.get('자리') or ['—'])}")
if not_done:
    blocked.append(f"요청 **{len(not_done)}건**이 아직 「재서 확인됨」이 아닙니다")

print()
print(f"ㄴ 판본 — 「재서 확인됨」 {len(items) - len(not_done)}건 중 "
      f"**이 마스터({FP})에서 확인된 것 {len(items) - len(not_done) - len(stale)}건**")
for i, x in stale:
    print(f"    ← {i}번 판본 **{x.get('판본')}** 에서 확인했습니다 — 이 마스터가 아닙니다")
    print(f"       {x['요청'][:60]}{'…' if len(x['요청']) > 60 else ''}")
if stale:
    blocked.append(f"**{len(stale)}건**이 다른 판본에서 확인됐습니다 — 이 마스터에서 다시 재세요")

# ── ㄷ 최종 편집자 판정 ─────────────────────────────────────────────────────
print()
if not ver_p.exists():
    print(f"ㄷ 편집자 판정 — **파일이 없습니다** ({ver_p.name})")
    blocked.append(f"최종 편집자 판정 파일이 없습니다: `script/{ver_p.name}`")
else:
    vs = json.loads(ver_p.read_text(encoding="utf-8"))
    vs = vs["판정"] if isinstance(vs, dict) else vs
    mine = [v for v in vs if v.get("판본") == FP]
    print(f"ㄷ 편집자 판정 — 기록 **{len(vs)}건** 중 **이 지문({FP})에 대한 것 {len(mine)}건**")
    for v in vs:
        mark = "●" if v.get("판본") == FP else "·"
        print(f"    {mark} {v.get('판본', '—')} · {v.get('본 때', '—')} · "
              f"짚은 것 {len(v.get('짚은 것') or [])}가지")
    if not mine:
        blocked.append(f"**이 마스터({FP})를 편집자가 안 봤습니다** — "
                       f"기록에 있는 것은 {' · '.join(sorted({v.get('판본', '—') for v in vs})) or '없음'}")

print()
if blocked:
    print("**막혔습니다.**")
    for b in blocked:
        print(f"  ← {b}")
    print()
    print("  **「사용자가 원한 뜻인가」는 여기서 안 봅니다** — 사람이 봅니다(총괄).")
    print("  이 관문이 묻는 것은 **「봤는가 · 어느 판본에서 봤는가」**까지입니다.")
    sys.exit(3)
print(f"**통과** — 대장 {len(items)}건 중 {len(items)}건 확인 · 편집자 판정 있음(지문 {FP})")
print("  **뜻이 맞는지는 여기서 안 봅니다.** 그건 사람이 봅니다(총괄).")
