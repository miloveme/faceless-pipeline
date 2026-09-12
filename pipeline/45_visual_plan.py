#!/usr/bin/env python3
"""씬별 화면 계획서를 만든다 — 사실은 스크립트가 채우고, 판단은 사람이 채운다.

대본을 다 쓰고 음성 길이가 나온 뒤(40단계 이후), 씬마다 어떤 화면을 쓸지 정해야 한다.
그 판단을 즉흥으로 하지 않도록 계획서를 표로 뽑는다.

스크립트가 채우는 것: 씬 번호, 길이, 섹션, 대본의 [V] 메모, 앞 씬과 같은 카드인지
사람(또는 AI)이 채우는 것: 카드 종류, 그 이유
승인된 계획서를 보고 `src/<slug>/scenes.tsx` 를 쓴다.

사용: 45_visual_plan.py <EP> [--force]
"""
import argparse
from common import *

# 카드 이름은 화면 문법과 같은 낱말을 쓴다 (Remotion/src/knowhow/grammars.json 의 carries).
# 어휘가 갈리면 46_grammar_check.py 가 대조를 못 한다.
CARDS = ["clip", "still", "contact", "compare", "log", "text", "table", "list",
         "diagram", "lead", "beats", "shot", "page", "whiteboard",
         # 제작 과정을 보이는 편에서 쓰는 셋. grammars.json 의 carries 와 같은 낱말이어야
         # 46_grammar_check 가 대조한다 — carries 는 미술 결과물이라 그쪽에서 넣는다.
         "prompt", "inout", "timeline"]
SOURCE_DESC = {
    "existing": "이미 있는 자산 — 원본 클립·스틸, 지난 프로젝트 파일",
    "record": "화면 녹화 — 터미널, 편집 화면, 브라우저 (OBS 등)",
    "gen-video": "AI 생성 영상",
    "gen-image": "AI 생성 이미지",
    "whiteboard": "손그림 애니메이션 (별도 도구로 렌더)",
    "code": "Remotion 이 직접 그림 — 텍스트, 표, 도식",
    "none": "소재 없이 화면만",
}

CARD_DESC = {
    "clip": "원본 영상 재생 — 증거를 그대로 보여줄 때",
    "still": "정지 프레임 한 장 또는 두 장 비교",
    "contact": "여러 장을 한 화면에 — 시간에 따른 변화",
    "compare": "좌우 동시 재생 → 정지 → 확대 — 전후 비교",
    "log": "터미널·로그 출력 — 실제로 돌린 기록을 그대로",
    "table": "표 — 항목과 값이 여러 행",
    "list": "목록 — 한 줄씩 쌓이는 항목",
    "lead": "큰 한 줄 — 바탕 위에 문장 하나 (무대 문법)",
    "beats": "짧은 줄 몇 개 — 상자 없이 차례로 (무대 문법)",
    "shot": "실제 화면 캡처 — 창 안에 그대로 (작업실 문법)",
    "page": "웹 페이지 — 브라우저 창 안에 (작업실 문법)",
    "text": "텍스트 카드 — 규칙, 정리, 결론",
    "diagram": "도식 — 관계나 구조를 그림으로(이 편 전용 컴포넌트)",
    "whiteboard": "손그림 애니메이션 — 단계가 쌓이는 설명, 볼 실물이 없을 때",
}

ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--force", action="store_true")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
if not p["scenes_v2"].exists(): die("scenes_v2.json 이 없습니다 — 먼저 40_nar_finalize.py 를 돌리세요.")
out = ep/"script"/"visual_plan.md"
if out.exists() and not a.force: die(f"이미 있습니다: {out}\n  다시 만들려면 --force (채워 둔 내용이 지워집니다)")

v2 = jload(p["scenes_v2"])["scenes"]
v1 = {s["id"]: s for s in jload(p["scenes_v1"])["scenes"]} if p["scenes_v1"].exists() else {}

rows = []
for s in v2:
    src = v1.get(s["id"], {})
    vis = src.get("visual") or {}
    # [V] 메모가 없으면(옛 형식) 남아 있는 정보라도 보여준다
    note = vis.get("note") or " · ".join(
        f"{k}={v}" for k, v in vis.items() if k != "note" and isinstance(v, str) and v)
    rows.append({"id": s["id"], "sec": round(s["t_end"] - s["t_start"], 1),
                 "section": src.get("section", ""), "title": src.get("title", ""), "note": note})

total = round(v2[-1]["t_end"], 1)
lines = [f"# 화면 계획 — {ep.name}", "",
         f"총 {len(rows)}씬 · {total}초 ({total/60:.1f}분)", "",
         "**카드 칸과 이유 칸을 채우세요.** 채우고 나면 이 표를 보고 `src/<slug>/scenes.tsx` 를 씁니다.",
         "",
         "## 정하기 전에 묻는 것",
         "1. 이 씬이 하려는 일은 무엇인가 — 증거를 보이는가, 개념을 풀어 주는가, 결론을 박는가.",
         "2. 그 일을 가장 짧게 해내는 화면은 무엇인가.",
         "3. 앞뒤와 붙였을 때 리듬이 사는가. (같은 카드 3연속은 46_grammar_check 가 셉니다 —\n   일부러 둔 자리면 script/grammar.json 의 `run_exceptions` 에 이유와 함께 적으세요.)",
         "",
         "**증거는 실물로.** 원본 클립·비교·인용 원문은 그림으로 대체하지 않습니다.",
         "",
         "## 쓸 수 있는 카드", ""]
lines += [f"- `{k}` — {d}" for k, d in CARD_DESC.items()]
lines += ["", "## 소재는 어디서 오나", ""]
lines += [f"- `{k}` — {d}" for k, d in SOURCE_DESC.items()]
lines += ["",
          "**증거로 쓰는 화면은 `existing` 이나 `record` 여야 합니다.** 생성한 그림은 증거가 될 수 없습니다.",
          "설명·분위기·개념 구간에만 `gen-*` 와 `whiteboard` 를 씁니다.", "",
          "## 계획", "",
          "| 씬 | 길이 | 섹션 | 대본의 [V] 메모 | 카드 | 소재 | 준비할 것 | 이유 |",
          "|---|---|---|---|---|---|---|---|"]
for r in rows:
    note = r["note"].replace("|", "/")[:50] or "—"
    lines.append(f"| {r['id']} {r['title'][:12]} | {r['sec']}초 | {r['section']} | {note} |  |  |  |  |")

lines += ["", "## 점검 (계획을 채운 뒤)", "",
          "- [ ] 증거 구간을 그림으로 대체하지 않았는가",
          "- [ ] 긴 씬에 정지 화면 한 장만 두지 않았는가 (길이 자체는 상한이 없다 — 움직이면 길어도 견딘다)",
          "- [ ] 화면 아래쪽에 글자를 둔 카드가 없는가 (자막과 겹친다)",
          "- [ ] 손그림을 넣었다면 한 편에 한 번인가, 그만한 값을 하는가",
          "- [ ] 증거 구간의 소재가 `existing` 또는 `record` 인가 (생성물로 대체하지 않았는가)",
          "- [ ] `준비할 것` 이 빈 씬은 소재가 이미 `source/` 에 있는가",
          "- [ ] 생성·녹화가 필요한 소재를 다 적었는가 (빠뜨리면 렌더 직전에 막힌다)", ""]

out.write_text("\n".join(lines), encoding="utf-8")
print(f"{len(rows)}개 씬 → {out}")
runs = [r["section"] for r in rows]
print(f"총 {total}초 · 가장 긴 씬 {max(rows, key=lambda r: r['sec'])['id']} {max(r['sec'] for r in rows)}초")
print("\n카드와 이유를 채운 뒤 사람 승인을 받고 scenes.tsx 를 쓰세요.")
