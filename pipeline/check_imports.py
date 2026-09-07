#!/usr/bin/env python3
"""올리는 파일이 부르는 것이 저장소에 다 있는지 본다.

클론한 사람이 컴파일할 수 있어야 한다. 내 기계에서 도는 것과 저장소가 받아서 도는 것은 다르다.
실제로 두 번 났다 — 부품 파일을 빼먹고 데이터만 올릴 뻔한 적, 그리고
`.gitignore` 가 막는 에피소드 폴더를 `Root.tsx` 가 부르게 될 뻔한 적.

보는 것은 **스테이지에 올라간 .ts/.tsx 의 상대경로 import** 다.
- 가리키는 파일이 없으면 실패
- 가리키는 파일이 **git 이 무시하는 것**이면 실패 — 내 기계에만 있고 클론에는 없다

훅이 부른다(`.githooks/pre-commit`). 걸리면 종료코드 3.
사용: check_imports.py [--staged | <파일...>]
"""
import re, subprocess, sys, pathlib

IMPORT = re.compile(r'(?:from|import)\s+["\'](\.[^"\']+)["\']')
EXTS = ("", ".ts", ".tsx", ".json", "/index.ts", "/index.tsx")

def git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout

def ignored(p: pathlib.Path) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", str(p)]).returncode == 0

args = [a for a in sys.argv[1:] if a != "--staged"]
if args:
    files = [pathlib.Path(f) for f in args]
else:
    files = [pathlib.Path(f) for f in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split("\n")
             if f.endswith((".ts", ".tsx"))]

bad = []
for f in files:
    if not f.exists(): continue
    seen = set()
    for line in f.read_text(encoding="utf-8").split("\n"):
        s = line.lstrip()
        if s.startswith("//") or s.startswith("*") or s.startswith("/*"): continue   # 주석의 예시는 넘어간다
        m = IMPORT.search(line)
        if not m: continue
        spec = m.group(1)
        if spec in seen: continue
        seen.add(spec)
        base = (f.parent / spec)
        hit = next((c for c in (pathlib.Path(str(base) + e) for e in EXTS) if c.is_file()), None)
        if hit is None:
            bad.append((f, spec, "가리키는 파일이 없습니다"))
        elif ignored(hit):
            bad.append((f, spec, f"git 이 무시하는 파일입니다 ({hit}) — 클론하면 없습니다"))

if bad:
    print(f"의존 검사 실패 — {len(bad)}건", file=sys.stderr)
    for f, spec, why in bad:
        print(f"  {f}  →  {spec}\n    {why}", file=sys.stderr)
    print("\n  올리는 파일이 부르는 것은 저장소에 있어야 합니다. 클론한 사람이 컴파일할 수 있어야 합니다.\n"
          "  무시되는 것을 부르고 있다면 그 줄을 빼고 올리거나, 무시 범위를 사용자와 정하세요.", file=sys.stderr)
    sys.exit(3)
print(f"의존 검사: 파일 {len(files)}개 · 걸린 것 0건")
