#!/usr/bin/env python3
"""문서가 적어 둔 `--옵션` 이 실제로 있는 옵션인가.

**없는 손잡이는 조용히 번진다.** `--attempt` 는 파이프라인 어디에도 없는 옵션인데
`voice.json` → `CLAUDE.md` → 담당 정의 파일로 퍼져 있었다. 읽은 사람이 그대로 치면
argparse 가 죽지만, **그 전에 「그렇게 하면 된다」고 믿고 계획을 세운다.**
실제 손잡이는 `20_tts_generate.py --seed N` 과 `35_nar_retry.py --ids <씬> --tries N` 이었다.

문서는 코드보다 늦게 낡는다. 코드에서 옵션을 지워도 문서는 남고, 아무도 안 운다.

보는 것: 문서의 **백틱 안 `--옵션`** (`` `--ids` `` 처럼).
대는 곳: `pipeline/**/*.py` 의 `add_argument("--…")` 전부.

**예외는 이 파일에 이름과 이유를 적는다.** 목록으로 두면 왜 뺐는지가 남는다 —
주석 없이 빼면 다음 사람이 「이건 왜 통과하지」를 다시 조사한다.

종료코드: 0 통과 · 2 설정 오류 · 3 없는 옵션이 문서에 있음
사용: check_docs_cli.py [--root <저장소>]
"""
import argparse, pathlib, re, sys

# 파이프라인 것이 아니라서 여기서 안 재는 옵션. **이름마다 「어느 파일에서」와 이유를 적는다.**
#
# **옵션 이름만으로 빼면 안 된다.** 처음에 `--attempt` 를 이름으로 빼 놨더니,
# `shell` 제공자 예제를 봐주려던 예외가 **CLAUDE.md 의 잘못된 `--attempt` 까지 통과시켰다** —
# 잡으려고 만든 바로 그 건이다. 예외는 **그 파일 안에서만** 듣는다.
#
# 지금은 비어 있다. `shell` 제공자의 `--in/--out/--attempt` 는 전부 펜스 친 코드 블록 안이라
# 백틱 한 쌍으로 감싼 자리가 없어서 애초에 안 걸린다 — 빼 줄 필요가 없었다.
EXEMPT: dict[str, tuple[list[str], str]] = {
    # "--보기": (["docs/어느파일.md"], "왜 파이프라인 옵션이 아닌지"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=None, help="저장소 뿌리 (기본: 이 파일의 상위)")
a = ap.parse_args()
ROOT = pathlib.Path(a.root).resolve() if a.root else pathlib.Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"
if not PIPE.is_dir():
    print(f"ERROR: pipeline/ 이 없습니다: {PIPE}", file=sys.stderr); sys.exit(2)

# ── 실재하는 옵션 모으기 ────────────────────────────────────────────────
# `add_argument("--x")` · `add_argument("-v", "--verbose")` 둘 다 잡는다.
ADD = re.compile(r'add_argument\(\s*((?:["\'][^"\']+["\']\s*,\s*)*["\'][^"\']+["\'])')
OPT = re.compile(r'["\'](--[A-Za-z0-9][A-Za-z0-9-]*)["\']')
real = {}
for f in sorted(PIPE.rglob("*.py")):
    try: src = f.read_text(encoding="utf-8")
    except OSError: continue
    for m in ADD.finditer(src):
        for o in OPT.findall(m.group(1)):
            real.setdefault(o, []).append(f.name)

# ── 문서에서 백틱 안 옵션 뽑기 ──────────────────────────────────────────
DOC_GLOBS = ["docs/*.md", "CLAUDE.md", "README.md",
             ".claude/agents/*.md", "skills/**/*.md", "pipeline/README.md", "remotion/README.md"]
docs = []
for g in DOC_GLOBS:
    docs.extend(sorted(ROOT.glob(g)))
docs = sorted({d for d in docs if d.is_file()})
if not docs:
    print(f"ERROR: 문서를 하나도 못 찾았습니다 (뿌리 {ROOT})", file=sys.stderr); sys.exit(2)

TICK = re.compile(r'`(--[A-Za-z0-9][A-Za-z0-9-]*)`')
bad, n_mentions = [], 0
for d in docs:
    for i, line in enumerate(d.read_text(encoding="utf-8").split("\n"), 1):
        rel = d.relative_to(ROOT).as_posix()
        for o in TICK.findall(line):
            n_mentions += 1
            if o in real: continue
            if o in EXEMPT and rel in EXEMPT[o][0]: continue   # **그 파일에서만** 봐준다
            bad.append((d.relative_to(ROOT), i, o, line.strip()[:100]))

if bad:
    print(f"문서 옵션 검사 실패 — {len(bad)}건", file=sys.stderr)
    for f, i, o, ctx in bad:
        print(f"  {f}:{i}  {o}   {ctx}", file=sys.stderr)
        near = [k for k in real if k.lstrip("-").startswith(o.lstrip("-")[:3])]
        if near: print(f"      비슷한 것: {', '.join(sorted(near))}", file=sys.stderr)
    print(f"\n  `pipeline/` 의 add_argument 에 없는 옵션입니다. 문서를 고치거나, 그 옵션을 만드세요.\n"
          f"  파이프라인 것이 아니면 check_docs_cli.py 의 EXEMPT 에 **이유와 함께** 넣으세요.", file=sys.stderr)
    sys.exit(3)
print(f"문서 옵션 검사: 문서 {len(docs)}개 · 백틱 옵션 {n_mentions}번 "
      f"(서로 다른 {len({o for d in docs for o in TICK.findall(d.read_text(encoding='utf-8'))})}종) · "
      f"파이프라인 옵션 {len(real)}종과 대조 · 걸린 것 0건")
