#!/usr/bin/env python3
"""올리는 파일이 부르는 것이 저장소에 다 있는지 본다.

클론한 사람이 컴파일할 수 있어야 한다. 내 기계에서 도는 것과 저장소가 받아서 도는 것은 다르다.
실제로 두 번 났다 — 부품 파일을 빼먹고 데이터만 올릴 뻔한 적, 그리고
`.gitignore` 가 막는 에피소드 폴더를 `Root.tsx` 가 부르게 될 뻔한 적.

보는 것은 **.ts/.tsx 의 상대경로 import** 다.
- 가리키는 파일이 없으면 실패
- 가리키는 파일이 **git 이 무시하는 것**이면 실패 — 내 기계에만 있고 클론에는 없다

  --staged     커밋 직전. 스테이지에 올라간 .ts/.tsx (pre-commit 훅)
  --range A..B 밀기 직전. 그 범위가 건드린 .ts/.tsx 를 **커밋 B 의 저장소 안에서** 본다 (pre-push 훅)
  <파일...>    직접 지정

**`--range` 가 따로 있는 이유**: `--staged` 는 그 커밋에 올라간 것만 본다.
`Root.tsx` 가 무시되는 편 폴더를 부르는 채로 트리에 **몇 시간 있었는데 아무도 안 울렸다** —
한 번도 스테이지에 안 올라갔기 때문이다. 밀기 직전에는 **범위 전체**를 다시 봐야 한다.
그리고 그때는 작업 폴더가 아니라 **커밋 안의 트리**를 봐야 한다. 클론한 사람이 받는 것이 그것이다.

훅이 부른다(`.githooks/pre-commit` · `.githooks/pre-push`). 걸리면 종료코드 3.
사용: check_imports.py [--staged | --range A..B | <파일...>]
"""
import posixpath, re, subprocess, sys, pathlib

IMPORT = re.compile(r'(?:from|import)\s+["\'](\.[^"\']+)["\']')
EXTS = ("", ".ts", ".tsx", ".json", "/index.ts", "/index.tsx")

def git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout

def ignored(p) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", str(p)]).returncode == 0

def tree_has(rev: str, path: str) -> bool:
    """커밋 `rev` 의 트리에 그 경로가 있나. **작업 폴더가 아니라 저장소를 본다.**"""
    return subprocess.run(["git", "cat-file", "-e", f"{rev}:{path}"],
                          capture_output=True).returncode == 0

def specs(text: str):
    """그 파일이 부르는 상대경로들. 주석의 예시는 넘어간다."""
    seen = set()
    for line in text.split("\n"):
        s = line.lstrip()
        if s.startswith("//") or s.startswith("*") or s.startswith("/*"): continue
        m = IMPORT.search(line)
        if not m: continue
        if m.group(1) in seen: continue
        seen.add(m.group(1)); yield m.group(1)

argv = sys.argv[1:]
rng = None
if "--range" in argv:
    i = argv.index("--range")
    if i + 1 >= len(argv):
        print("ERROR: --range 에 범위가 없습니다 (예: origin/main..HEAD)", file=sys.stderr); sys.exit(2)
    rng = argv[i + 1]; del argv[i:i + 2]
args = [x for x in argv if x != "--staged"]

bad, scope = [], ""

if rng:
    # 범위의 **끝 커밋**이 클론한 사람이 받는 트리다. `A..B` · `A...B` · 단일 sha 를 다 받는다.
    rev = rng.split("...")[-1].split("..")[-1] or "HEAD"
    rev = (git("rev-parse", "--short", rev).strip() or rev)   # 메시지에 HEAD 말고 실제 sha 를 찍는다
    names = sorted({f for f in git("log", "--diff-filter=ACMR", "--name-only", "--format=", rng).split("\n")
                    if f.endswith((".ts", ".tsx"))})
    checked = 0
    for f in names:
        if not tree_has(rev, f): continue          # 뒤 커밋에서 지워졌다 — 클론에는 없으니 볼 것도 없다
        checked += 1
        for spec in specs(git("show", f"{rev}:{f}")):
            base = posixpath.normpath(posixpath.join(posixpath.dirname(f), spec))
            if not any(tree_has(rev, base + e) for e in EXTS):
                bad.append((f, spec, f"커밋 {rev[:7]} 의 저장소 안에 없습니다 — 클론하면 컴파일이 안 됩니다"))
    scope = f"범위 {rng} · 그 범위가 건드린 .ts/.tsx {checked}개"
else:
    if args:
        files = [pathlib.Path(f) for f in args]
    else:
        files = [pathlib.Path(f) for f in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split("\n")
                 if f.endswith((".ts", ".tsx"))]
    for f in files:
        if not f.exists(): continue
        for spec in specs(f.read_text(encoding="utf-8")):
            base = (f.parent / spec)
            hit = next((c for c in (pathlib.Path(str(base) + e) for e in EXTS) if c.is_file()), None)
            if hit is None:
                bad.append((f, spec, "가리키는 파일이 없습니다"))
            elif ignored(hit):
                bad.append((f, spec, f"git 이 무시하는 파일입니다 ({hit}) — 클론하면 없습니다"))
    scope = f"파일 {len(files)}개"

if bad:
    print(f"의존 검사 실패 — {len(bad)}건", file=sys.stderr)
    for f, spec, why in bad:
        print(f"  {f}  →  {spec}\n    {why}", file=sys.stderr)
    print("\n  올리는 파일이 부르는 것은 저장소에 있어야 합니다. 클론한 사람이 컴파일할 수 있어야 합니다.\n"
          "  무시되는 것을 부르고 있다면 그 줄을 빼고 올리거나, 무시 범위를 사용자와 정하세요.", file=sys.stderr)
    sys.exit(3)
print(f"의존 검사: {scope} · 걸린 것 0건")
