#!/usr/bin/env python3
"""렌더를 묶은 뒤에 바뀐 원본을 센다. `60_render_master.sh` 가 부른다.

**렌더 도중에 고친 것은 그 마스터에 안 든다.** Remotion 이 시작할 때 한 번 묶기 때문인데,
아무 말도 안 하고 옛 판본을 끝까지 굽는다. 그래서 고친 사람이 「고친 것이 이렇게 나왔다」를
그 마스터로 보고하게 된다 — 2026-09-08 v9 에서 실제로 났다.

첫 줄에 **본 파일 수**, 그 다음 줄부터 **묶은 뒤에 바뀐 파일**을 최근 것부터 찍는다.
「없다」를 셀 때 몇 개를 봤는지 같이 찍어야 검사가 깨진 것과 구별된다.
"""
import sys
import pathlib

root, at = pathlib.Path(sys.argv[1]), float(sys.argv[2])
seen, late = 0, []
for d in ("src", "public"):
    p = root / d
    if not p.exists():
        continue
    for f in p.rglob("*"):
        if not f.is_file() or "node_modules" in f.parts:
            continue
        seen += 1
        if f.stat().st_mtime > at:
            late.append((f.stat().st_mtime, f.relative_to(root)))
print(seen)
for _m, f in sorted(late, reverse=True):
    print(f)
