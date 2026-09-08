#!/usr/bin/env python3
"""**사용자가 요청한 것이 들어갔나.** `script/requests.json` 을 읽어 표로 찍고, **근거가 있는지**를 잰다.

우리 잣대는 대비·비율·정지·무음·겹말인데 **「사용자가 요청한 것이 들어갔나」를 재는 것이
하나도 없었다.** 사용자가 **「내가 요청한 것은 담당이 미리 확인해서 수정했어야 하는 것 아니냐」**고
물었고 맞다 — 2026-09-09 E01 에서 사용자가 직접 찾아야 했다.

**기계가 못 보는 것과 볼 수 있는 것을 가른다.**
```
못 본다   「그 문구가 사용자가 원한 뜻인가」          ← 사람이 본다. 그 사람이 총괄이다
본다     **「재서 확인됨」이라고 적었는데 근거가 있나** — 판본이 있나 · 그 자리가 있나
```
「들어감」과 **「재서 확인됨」**을 가르는 것이 이 표의 값이다.
같은 하루에 **「승인했다 · 들어갔다 · 셌다 · 효과 0 · 넘겼다 · 보냈다」가 여섯 번** 났다 —
전부 「했다고 말한 것」과 「그렇게 된 것」이 갈린 자리다. **사용자 요청에서 그러면 사용자가 두 번 말한다.**

**여기서 내용을 채우지 않는다.** 무엇이 요청이었는지는 총괄이 안다.

사용: 07_requests_check.py <EP>
종료코드: 0 통과 · 2 설정 오류 · 3 **근거가 없는 「재서 확인됨」이 있다**
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ep_dir  # noqa: E402

STATES = ["안 들어감", "들어감", "재서 확인됨"]


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


if len(sys.argv) < 2:
    die("사용: 07_requests_check.py <EP>")
ep = ep_dir(sys.argv[1])
p = ep / "script" / "requests.json"
if not p.exists():
    die(f"요청 대장이 없습니다: {p}\n"
        f"  **이 파일은 총괄이 씁니다** — 무엇이 요청이었는지는 사용자 말을 받은 쪽만 압니다.\n"
        f"  꼴: {{\"_\": [...], \"요청\": [{{\"요청\": \"…\", \"자리\": [\"…\"], \"담당\": \"…\",\n"
        f"       \"상태\": \"{'|'.join(STATES)}\", \"판본\": \"sha1 앞 8자\", \"잰 것\": \"…\"}}]}}")

doc = json.loads(p.read_text(encoding="utf-8"))
items = doc["요청"] if isinstance(doc, dict) else doc

# 이 편에 있는 마스터의 지문 — 「재서 확인됨」이 가리키는 판이 실제로 있나.
# **그리고 그것이 「지금 마스터」인가.** 「있나」는 「그때는 그랬다」까지고,
# 「지금도 그런가」는 다른 물음이다(음악 감독). s07 은 **대본이 아니라 렌더가 흘린 것**이라
# **판마다 다시 날 수 있다** — 「한 번 확인했으니 끝」이 성립하지 않는 종류다.
# **막지 않고 찍는다.** 판이 바뀔 때마다 열일곱 줄이 다 빨개지면 대장을 안 본다(총괄).
masters = {}
# **마스터만 본다.** 프리뷰까지 세면 목록이 길어져 「어느 판인가」가 안 보인다.
for m in sorted((ep / "edit").glob("*_master.mp4")):
    try:
        masters[subprocess.run(["shasum", "-a", "1", str(m)], capture_output=True,
                               text=True).stdout[:8]] = m.name
    except Exception:
        pass

# **지금 마스터** = `edit/` 에서 제일 나중에 고쳐진 `*_episode_*_master.mp4`
_eps = sorted((ep / "edit").glob("*_episode_*_master.mp4"), key=lambda f: f.stat().st_mtime)
NOW = None
if _eps:
    NOW = subprocess.run(["shasum", "-a", "1", str(_eps[-1])], capture_output=True,
                         text=True).stdout[:8]

sc = ep / "script" / "scenes_v1.json"
SCENES = set()
if sc.exists():
    d = json.loads(sc.read_text(encoding="utf-8"))
    SCENES = {x["id"] for x in (d["scenes"] if isinstance(d, dict) else d)}

REPO = pathlib.Path(__file__).resolve().parent.parent
SID = re.compile(r"^s\d\d$")

print(f"사용자 요청 **{len(items)}건** · 이 편의 마스터 **{len(masters)}개** — "
      + (" · ".join(f"{k} {v.replace('_master.mp4', '')}" for k, v in masters.items())
         if masters else "**없음**"))
print()

print(f"**지금 마스터**: {NOW} {_eps[-1].name}" if NOW else "**지금 마스터가 없습니다**")
print()

bad, cnt, old_v = [], {s: 0 for s in STATES}, []
for i, it in enumerate(items, 1):
    st = it.get("상태", "")
    if st not in STATES:
        die(f"{i}번의 `상태` 를 모르겠습니다: {st!r}\n  쓸 수 있는 것: {' · '.join(STATES)}")
    cnt[st] += 1
    mark = {"안 들어감": "· ", "들어감": "◐ ", "재서 확인됨": "● "}[st]
    print(f"{mark}**{st}**  {it['요청']}")
    print(f"     담당 {it.get('담당', '—')}"
          + (f" · 판본 {it['판본']}" if it.get("판본") else "")
          + (f" · 잰 것 {it['잰 것']}" if it.get("잰 것") else ""))
    where = it.get("자리") or []
    if where:
        print(f"     자리 {' · '.join(where)}")
    # ── 기계가 볼 수 있는 것 ①: 「재서 확인됨」은 판본이 있어야 한다
    if st == "재서 확인됨":
        v = it.get("판본")
        if not v:
            bad.append(f"{i}번 「재서 확인됨」인데 **판본이 없습니다** — 어느 마스터에서 쟀습니까")
        elif not masters:
            # **못 대는 것을 통과시키지 않는다.** 마스터가 없으면 「재서 확인됨」을 확인할 방법이 없다 —
            # 조용히 넘기면 아무 지문이나 적어도 초록이 된다.
            bad.append(f"{i}번 판본 **{v}** 를 댈 마스터가 `edit/` 에 **하나도 없습니다** — "
                       f"못 대는 것은 통과가 아닙니다")
        elif v not in masters:
            bad.append(f"{i}번 판본 **{v}** 인 마스터가 `edit/` 에 없습니다 "
                       f"(있는 것: {' · '.join(masters)})")
        if not it.get("잰 것"):
            bad.append(f"{i}번 「재서 확인됨」인데 **잰 것이 없습니다** — 수 없이 확인은 안 됩니다")
        if v and NOW and v != NOW:
            old_v.append((i, it["요청"], v))
            print(f"     ← **옛 판({v})에서 확인한 것입니다.** 지금 마스터는 {NOW} — "
                  f"「그때는 그랬다」입니다")
    # ── ②: 적어 둔 자리가 실제로 있나
    for w in where:
        if SID.match(w):
            if SCENES and w not in SCENES:
                bad.append(f"{i}번 자리 **{w}** 은 지금 대본에 없는 씬입니다")
            continue
        if w == "자리 미정":
            continue
        f, _, ln = w.partition(":")
        fp = REPO / f
        if not fp.exists():
            bad.append(f"{i}번 자리 **{w}** — 그 파일이 없습니다")
        elif ln.isdigit() and len(fp.read_text(encoding="utf-8", errors="ignore").splitlines()) < int(ln):
            bad.append(f"{i}번 자리 **{w}** — 그 파일이 {ln}줄보다 짧습니다")
    print()

_now_n = cnt["재서 확인됨"] - len(old_v)
print(f"안 들어감 **{cnt['안 들어감']}** · 들어감 **{cnt['들어감']}** · "
      f"재서 확인됨 **{cnt['재서 확인됨']}** / 모두 {len(items)}건")
print(f"  재서 확인됨 중 — **지금 마스터에서 {_now_n}건** · **옛 판에서 {len(old_v)}건**"
      + (f" (다시 재야 할 것: {' · '.join(f'{i}번' for i, _, _ in old_v)})" if old_v else ""))
print("  **「들어감」과 「재서 확인됨」은 다릅니다** — 앞엣것은 코드에 넣은 것이고 "
      "뒤엣것은 **그 마스터에서 재 본 것**입니다.")
print("  **「그 문구가 사용자가 원한 뜻인가」는 여기서 안 봅니다** — 사람이 봅니다(총괄).")
if bad:
    print()
    print("근거가 없는 것:")
    for b in bad:
        print(f"  ← {b}")
    sys.exit(3)
