#!/usr/bin/env python3
"""**새로 클론한 사본이 컴파일되는가.** 내 기계에서 도는 것과 저장소가 받아서 도는 것은 다르다.

`remotion/src/e01/` 은 `.gitignore` 에 있다. 그 폴더를 부르는 `Root.tsx` 를 올리면
**내 기계에서는 `tsc` 가 통과한다** — 폴더가 있으니까. 받아 간 사람만 깨진다.
실제로 그 상태로 커밋될 뻔했고, 클론을 떠서 재고서야 보였다.

`check_imports.py` 가 같은 자리를 **싸게** 본다(import 한 줄씩). 이 검사는 **비싸게** 본다 —
진짜로 클론을 떠서 `npx tsc --noEmit` 을 돌린다. import 로는 안 보이는 것이 잡힌다:
타입이 안 맞는 것, `tsconfig` 가 가리키는 파일이 빠진 것, 설정 파일이 안 올라간 것.

**`node_modules` 는 새로 안 받는다.** 이 검사가 보는 것은 *소스가 다 올라갔는가* 지
*의존성을 받을 수 있는가* 가 아니다. 있는 것을 심링크로 빌려 쓴다 — `npm install` 은 몇 분이고
pre-push 에 둘 수 없다. 빌려 올 것이 없으면 **건너뛰고 그 사실을 찍는다**(조용히 통과하지 않는다).

종료코드: 0 통과(또는 건너뜀) · 2 설정 오류 · 3 클론이 컴파일 안 됨
사용: check_clone_build.py [--rev HEAD] [--repo <경로>] [--keep]
"""
import argparse, os, pathlib, shutil, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("--rev", default="HEAD", help="이 커밋의 트리를 본다 (기본 HEAD)")
ap.add_argument("--repo", default=None, help="저장소 (기본: 이 파일의 상위)")
ap.add_argument("--keep", action="store_true", help="clone 한 폴더를 안 지운다 (들여다볼 때)")
a = ap.parse_args()

REPO = pathlib.Path(a.repo).resolve() if a.repo else pathlib.Path(__file__).resolve().parent.parent
if not (REPO / ".git").exists():
    print(f"ERROR: git 저장소가 아닙니다: {REPO}", file=sys.stderr); sys.exit(2)

def run(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

rev = run("git", "rev-parse", "--short", a.rev, cwd=REPO).stdout.strip()
if not rev:
    print(f"ERROR: 그런 커밋이 없습니다: {a.rev}", file=sys.stderr); sys.exit(2)

# 빌려 올 node_modules. 작업 폴더의 것을 쓴다.
nm = pathlib.Path(os.environ.get("REMOTION_DIR") or (REPO / "remotion")) / "node_modules"
if not nm.is_dir():
    print(f"클론 빌드 검사: **건너뜀** — 빌려 올 node_modules 가 없습니다 ({nm})\n"
          f"  이 검사는 소스가 다 올라갔는지만 봅니다. 의존성을 받는 것은 보지 않습니다.\n"
          f"  돌리려면: cd {REPO/'remotion'} && npm install")
    sys.exit(0)

tmp = pathlib.Path(tempfile.mkdtemp(prefix="clonebuild-"))
try:
    c = run("git", "clone", "-q", "--no-checkout", str(REPO), str(tmp / "repo"))
    if c.returncode != 0:
        print(f"ERROR: clone 실패\n{c.stderr}", file=sys.stderr); sys.exit(2)
    dst = tmp / "repo"
    c = run("git", "checkout", "-q", rev, cwd=dst)
    if c.returncode != 0:
        print(f"ERROR: 그 커밋을 못 꺼냈습니다 ({rev})\n{c.stderr}", file=sys.stderr); sys.exit(2)

    rem = dst / "remotion"
    if not (rem / "package.json").is_file():
        print(f"클론 빌드 검사: **건너뜀** — 커밋 {rev} 에 remotion/package.json 이 없습니다")
        sys.exit(0)
    (rem / "node_modules").symlink_to(nm)

    # 편 폴더가 정말 없는 사본인지 같이 찍는다 — 이 검사의 값어치가 거기 있다.
    eps = sorted(p.name for p in (rem / "src").glob("e[0-9][0-9]")) if (rem / "src").is_dir() else []
    t = run("npx", "tsc", "--noEmit", cwd=rem)
    if t.returncode != 0:
        print(f"클론 빌드 검사 실패 — 커밋 {rev} 를 새로 클론하면 컴파일이 안 됩니다", file=sys.stderr)
        for line in (t.stdout + t.stderr).strip().split("\n")[:20]:
            print(f"  {line}", file=sys.stderr)
        print("\n  이 기계에서는 통과할 수 있습니다 — `.gitignore` 가 막는 파일이 여기엔 있기 때문입니다.\n"
              "  받아 간 사람에게는 없습니다. 저장소에 안 들어가는 것을 부르고 있지 않은지 보세요.", file=sys.stderr)
        sys.exit(3)
    print(f"클론 빌드 검사: 커밋 {rev} 를 새로 클론해 `npx tsc --noEmit` 통과 · "
          f"그 사본의 편 폴더 {len(eps)}개{' ' + ', '.join(eps) if eps else ' (없음 — 클론한 사람이 받는 상태)'}")
finally:
    if a.keep: print(f"  clone 남김: {tmp}")
    else: shutil.rmtree(tmp, ignore_errors=True)
