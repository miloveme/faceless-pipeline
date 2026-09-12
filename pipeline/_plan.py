#!/usr/bin/env python3
"""화면 계획서(`script/visual_plan.md`)의 표를 읽는다.

`46_grammar_check` 와 `85_ship_gate` 가 같은 표를 본다. **옮겨 적으면 둘이 갈린다** —
열 이름이 편마다 다른데(45 템플릿은 「이유」, E01 은 「이해시킬 것」) 한쪽만 고치면
다른 쪽이 조용히 「열이 없다」로 읽는다.

**여기 있는 것은 읽기뿐이다.** 판정은 부르는 쪽이 한다.
"""
import re

# 「왜 그 카드인가」가 적히는 열. 이름이 편마다 다르다.
REASON_COLS = ("이유", "이해시킬 것")


def plan_cards(plan_text: str):
    """계획서 표에서 씬별 카드와 이유를 뽑는다.

    **머리글을 만난 그 표만 읽고 표가 끝나면 멈춘다.** 예전에는 인덱스를 그 뒤 모든 `|` 줄에
    적용해서, 뒤에 오는 다른 표(씬 id 로 시작하는 박자 표·슬롯 표)가 카드를 덮어썼다 —
    카드가 「글」·「8.8」 로 읽혔고 검사는 엉뚱한 이유로 종료코드 3 을 냈다.

    반환: (씬→카드, 씬→이유, 이유 열이 있었나)
    """
    used, reasons = {}, {}
    i_scene = i_card = i_reason = None
    ncol = 0
    had_reason_col = False
    for line in plan_text.splitlines():
        if not line.startswith("|"):
            i_scene = i_card = i_reason = None   # 표가 끝났다. 다음 머리글을 다시 기다린다
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if "카드" in cells and "씬" in cells:
            i_scene, i_card, ncol = cells.index("씬"), cells.index("카드"), len(cells)
            i_reason = next((cells.index(r) for r in REASON_COLS if r in cells), None)
            had_reason_col = had_reason_col or i_reason is not None
            continue
        if i_card is None or len(cells) != ncol:
            continue
        m = re.match(r"(s\d{2})", cells[i_scene].strip("*` "))
        card = cells[i_card].strip("*` ")
        if m and card:
            used[m.group(1)] = card
            if i_reason is not None:
                reasons[m.group(1)] = cells[i_reason].strip("*` ")
    return used, reasons, had_reason_col
