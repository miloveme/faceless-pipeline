#!/usr/bin/env python3
"""대본 마크다운 → 씬 JSON.

사람은 마크다운으로 대본을 쓰고(읽고 고치기 쉬우니까), 공정은 JSON을 읽는다.
이 스크립트가 그 사이를 잇는다.

대본 형식:

    ## s00 훅
    [V] 화면에 무엇을 띄울지
    [N] 실제로 읽을 문장.

    ## s01 전제
    [V] ...
    [N] ...

규칙
- `## s<번호> <제목>` 이 씬 하나를 연다.
- `[V]` 비주얼 지시, `[N]` 내레이션. 둘 다 다음 줄로 이어 써도 된다.
- `[N]` 이 없는 씬은 오류다(읽을 문장이 없으면 씬이 아니다).
- `##` 로 시작하지 않는 문단(제목·메모)과 `[미결]` 같은 다른 태그 줄은 무시한다.
- 씬 번호가 순서대로가 아니면 알려준다. `--renumber` 를 주면 순서대로 다시 매긴다
  (마크다운 파일도 함께 고친다).

section 은 자동으로 붙는다: 첫 씬 hook, 마지막 outro, 그 앞 rule, 나머지 body.
대본에 `[S] <이름>` 을 쓰면 그 값이 우선한다.

사용: 05_script_to_scenes.py <EP> [--md script/script_v1.md] [--renumber]
"""
import argparse, re
from common import *

ap = argparse.ArgumentParser(); ap.add_argument("ep")
ap.add_argument("--md", default="script/script_v1.md")
ap.add_argument("--renumber", action="store_true", help="씬 번호를 순서대로 다시 매긴다(md도 수정)")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
md_path = ep / a.md
if not md_path.exists(): die(f"대본이 없습니다: {md_path}")
text = md_path.read_text(encoding="utf-8")

HEAD = re.compile(r"^##\s+(s\d+)\s*(.*)$")
TAG = re.compile(r"^\[([VNS])\]\s*(.*)$")
ANYTAG = re.compile(r"^\[[^\]]{1,12}\]")   # [미결] 같은 다른 태그 — 이어쓰기를 끊는다

scenes, cur, field = [], None, None
for line in text.split("\n"):
    m = HEAD.match(line)
    if m:
        cur = {"id": m.group(1), "title": m.group(2).strip(), "visual": "", "narration": "", "section": ""}
        scenes.append(cur); field = None; continue
    if cur is None: continue
    t = TAG.match(line)
    if t:
        field = {"V": "visual", "N": "narration", "S": "section"}[t.group(1)]
        cur[field] = t.group(2).strip(); continue
    if line.startswith("##"): cur, field = None, None; continue   # 다른 절이 시작되면 씬 종료
    if ANYTAG.match(line): field = None; continue                 # [미결] 등 — 여기서 이어쓰기 끝
    if field and line.strip(): cur[field] += " " + line.strip()   # 이어지는 줄

if not scenes: die("씬을 하나도 못 찾았습니다. `## s00 제목` 형식인지 확인하세요.")

missing = [s["id"] for s in scenes if not s["narration"]]
if missing:
    if len(missing) >= len(scenes) - 2:
        die(f"대본이 아직 비어 있습니다 ({len(missing)}/{len(scenes)} 씬에 [N] 이 없음).\n"
            f"  {md_path} 를 열어 각 씬의 [N] 에 읽을 문장을 쓰세요.\n"
            f"  형식: docs/SCRIPT_FORMAT.md")
    die("[N] 이 없는 씬: " + ", ".join(missing) +
        "\n  읽을 문장이 없으면 씬이 아닙니다. 문장을 넣거나 그 씬을 지우세요.")

ids = [s["id"] for s in scenes]
want = [f"s{i:02d}" for i in range(len(scenes))]
if ids != want:
    if not a.renumber:
        bad = [f"{o}→{n}" for o, n in zip(ids, want) if o != n]
        die("씬 번호가 순서대로가 아닙니다: " + ", ".join(bad[:8]) +
            ("..." if len(bad) > 8 else "") + "\n  --renumber 를 주면 다시 매깁니다(마크다운도 함께 수정).")
    lines, n = text.split("\n"), 0
    for i, l in enumerate(lines):
        m = HEAD.match(l)
        if m: lines[i] = f"## s{n:02d} {m.group(2).strip()}".rstrip(); n += 1
    md_path.write_text("\n".join(lines), encoding="utf-8")
    for s, new in zip(scenes, want): s["id"] = new
    print(f"씬 번호 재정렬: {len(scenes)}개 → {md_path.name} 수정됨")

for i, s in enumerate(scenes):
    if not s["section"]:
        s["section"] = ("hook" if i == 0 else "outro" if i == len(scenes) - 1
                        else "rule" if i == len(scenes) - 2 else "body")

out = {"episode": ep.name, "title": (text.split("\n")[0].lstrip("# ").strip() or ep.name),
       "scenes": [{"id": s["id"], "section": s["section"], "title": s["title"],
                   "narration": s["narration"], "visual": {"note": s["visual"]}} for s in scenes]}
jdump(out, p["scenes_v1"])

# 자수는 길이(초)를 가늠하는 값이다. **강조** 표시는 음성이 읽지 않으므로(tts_preprocess 가 지운다) 세지 않는다.
spoken = lambda s: len(strip_emphasis(s["narration"]))
chars = sum(spoken(s) for s in scenes)
raw = sum(len(s["narration"]) for s in scenes)
print(f"{md_path.name} → {len(scenes)}개 씬 · {chars}자 · 약 {chars/8.5/60:.1f}분 (8.5자/초 기준) → {p['scenes_v1']}")
if raw != chars:
    print(f"  (자수는 음성이 읽는 글자만 셉니다. 대본 원문 {raw}자 − 강조 표시 ** {raw-chars}자)")
longest = max(scenes, key=spoken)
print(f"가장 긴 씬 {longest['id']} {spoken(longest)}자 ≈ {spoken(longest)/8.5:.0f}초")
print("\n다음: 10_tts_prep.py 로 숫자·영문 읽기를 전처리하세요.")
