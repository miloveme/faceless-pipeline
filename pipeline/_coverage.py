#!/usr/bin/env python3
"""적용 범위를 센다 — **몇 개 중 몇 개인가.**

`--ids` 로 일부만 다시 만들면 **나머지 씬은 옛 데이터로 남는다.** E00 에서 낱말 시각을
넣고 다섯 씬만 다시 만들었는데 「전 씬 적용」이라고 보고했다. 화면은 멀쩡해 보인다 —
낱말 시각이 없는 씬은 노래방 강조가 안 될 뿐 자막은 그대로 나온다.

이 셈은 `sound-director.md` 에 **파이썬 한 줄**로 박혀 있었다. 사람이 기억해서 치는 셈은
바쁠 때 안 친다. 50·55 끝에서 저절로 찍히게 한다.

**값이 아니라 범위를 대조한다.** `n/N` 하나만 찍으면 **N 자체가 반쪽일 때** 안 보인다 —
`captions.json` 안에서 152/152 라도, `scenes_v2.json` 에 있는 씬이 `captions.json` 에
아예 없으면 그 씬은 분모에도 없다. 그래서 **두 파일의 씬 집합을 양쪽으로** 본다.

종료코드: 0 (찍기만 한다) · 2 설정 오류 · 3 `--require-full` 인데 안 찬 것이 있음
사용: _coverage.py <EP> [--require-full]
"""
import argparse, sys
from common import P, die, ep_dir, jload

ap = argparse.ArgumentParser()
ap.add_argument("ep")
ap.add_argument("--require-full", action="store_true",
                help="하나라도 안 차면 종료코드 3 (전체를 다시 만든 직후에 쓴다)")
a = ap.parse_args()
ep = ep_dir(a.ep); p = P(ep)

lines, short = [], []

def say(label, n, N, note=""):
    pct = (100.0 * n / N) if N else 0.0
    mark = "" if (N and n == N) else "   ← 안 참"
    lines.append(f"  {label:32} {n:>4} / {N:<4} ({pct:5.1f}%){note}{mark}")
    if not N or n != N: short.append(f"{label} {n}/{N}")

# ── 씬 목록의 기준은 scenes_v2 다 ────────────────────────────────────────
if not p["scenes_v2"].exists():
    die(f"scenes_v2.json 이 없습니다: {p['scenes_v2']}\n  먼저 40_nar_finalize.py 를 돌리세요.", 2)
sc = jload(p["scenes_v2"])["scenes"]
sids = [s["id"] for s in sc]
say("씬 (scenes_v2 기준)", len(sids), len(sids))
say("내레이션 파일이 적힌 씬", sum(1 for s in sc if s.get("narration_file")), len(sids))
say("씬 시각(t_start·t_end)", sum(1 for s in sc if "t_start" in s and "t_end" in s), len(sids))

# ── 자막 ────────────────────────────────────────────────────────────────
if p["caps"].exists():
    caps = jload(p["caps"])
    cids = list(caps)
    rows = [x for ch in caps.values() for x in ch]
    say("자막 줄에 낱말 시각(words)", sum(1 for x in rows if "words" in x), len(rows))
    say("낱말 시각이 다 있는 씬", sum(1 for v in caps.values() if v and all("words" in x for x in v)), len(cids))
    # **범위 대조** — n/N 으로는 안 보이는 자리
    miss = [i for i in sids if i not in caps]
    extra = [i for i in cids if i not in sids]
    say("자막이 있는 씬 (scenes_v2 대비)", len([i for i in sids if i in caps]), len(sids))
    if miss:  lines.append(f"      자막이 **아예 없는** 씬 {len(miss)}개: {', '.join(miss)}")
    if extra: lines.append(f"      scenes_v2 에 없는데 자막에 있는 씬 {len(extra)}개: {', '.join(extra)}"
                           f"  ← 씬 번호가 밀린 판본의 자막이 남은 것일 수 있습니다")
    if miss or extra: short.append("자막 씬 집합이 scenes_v2 와 다름")
else:
    lines.append("  자막 (captions.json)             없음 — 50_captions_build.py 를 안 돌렸습니다")
    short.append("captions.json 없음")

# ── TTS 입력 ────────────────────────────────────────────────────────────
if p["tts_input"].exists():
    tts = jload(p["tts_input"])
    tids = {x["id"] for x in tts}
    say("TTS 입력이 있는 씬", len([i for i in sids if i in tids]), len(sids))
    say("바꾼 것(subs)이 적힌 씬", sum(1 for x in tts if "subs" in x), len(tts),
        "  ← 없으면 30단계 숫자 대조가 안 됩니다" if any("subs" not in x for x in tts) else "")

print(f"적용 범위 — {ep.name}")
print("\n".join(lines))
if short:
    print(f"  **안 찬 것 {len(short)}가지**: " + " · ".join(short))
    print("  `--ids` 로 일부만 돌렸다면 나머지는 **옛 데이터**입니다. 「전 씬 적용」이라고 적기 전에 이 줄을 보세요.")
    if a.require_full: sys.exit(3)
else:
    print("  전부 찼습니다.")
