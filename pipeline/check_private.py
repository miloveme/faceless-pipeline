#!/usr/bin/env python3
"""개인 자산이 저장소에 들어가는 것을 막는다. 이 저장소는 공개다 — 한 번 올라가면 지워도 남는다.

훅이 부른다(`.githooks/`, `check_setup.py` 가 연결). 사람이 기억해서 돌리는 검사가 아니다.

  --staged     커밋 직전. 스테이지에 올라간 파일 이름과 **추가된 줄**
  --msg-file F 커밋 메시지 파일 (commit-msg 훅)
  --range A..B 밀기 직전. 그 범위 커밋의 메시지와 추가된 줄
  (아무것도 안 주면) 지금 추적 중인 파일 전체의 이름과 내용

찾는 것: 개인 경로(/Users/·/home/·C:\\Users\\), 사설 IP, 이메일, MAC 주소, 이 기계의 이름,
그리고 새로 추적되는 미디어·개인 자산 파일.

**거짓 경보를 내지 않는 것이 더 중요하다.** 문서가 일부러 쓰는 값은 예외로 둔다 —
루프백 127.x, 문서 전용 대역(RFC 5737) 192.0.2.x·198.51.100.x·203.0.113.x,
커밋 트레일러의 noreply@ 주소. 사용자 계정명 자체는 찾지 않는다(`jun` 이 `junk` 에 걸린다).
계정명이 드러나는 자리는 경로라, 경로 모양으로 잡는다.

찾은 것이 있으면 종료코드 3, 없으면 0. 인자가 틀리면 2.
"""
import argparse, platform, re, socket, subprocess, sys, pathlib

def git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout

# 이름만으로 걸러야 하는 것 (.gitignore 와 겹치지만, ignore 는 이미 추적된 파일을 못 막는다)
BAD_NAME = re.compile(r"\.(mp3|wav|m4a|mp4|mov|avi|mkv|zip)$|(^|/)voice\.json$|^episodes/|^assets/(?!README\.md$)")
DOC_IP = re.compile(r"^(127\.|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)")
OK_MAIL = re.compile(r"^noreply@|@users\.noreply\.github\.com$|^[a-z]+@example\.(com|org)$")

def machine_names():
    """이 기계를 가리키는 이름들. 짧거나 흔한 것은 거짓 경보를 내므로 뺀다."""
    out = set()
    for n in (socket.gethostname(), platform.node()):
        n = (n or "").split(".")[0]
        if len(n) >= 6: out.add(n)
    for cmd in (["scutil", "--get", "ComputerName"], ["scutil", "--get", "LocalHostName"]):
        try:
            n = subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
            if len(n) >= 6: out.add(n)
        except Exception: pass
    return sorted(out)

MACHINE = machine_names()
PATTERNS = [
    ("개인 경로",  re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+")),
    ("사설 IP",    re.compile(r"(?<![\d.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}")),
    ("이메일",     re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("MAC 주소",   re.compile(r"(?<![:\w])(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}(?![:\w])")),
]
if MACHINE:
    PATTERNS.append(("기기 이름", re.compile("|".join(re.escape(n) for n in MACHINE), re.I)))

def scan_text(label, text, hits):
    for line_no, line in enumerate(text.split("\n"), 1):
        for what, pat in PATTERNS:
            for m in pat.finditer(line):
                if what == "사설 IP" and DOC_IP.match(m.group(0)): continue
                if what == "이메일" and OK_MAIL.search(m.group(0)): continue
                hits.append((label, line_no, what, m.group(0), line.strip()[:100]))

def added_lines(*log_args):
    return "\n".join(l[1:] for l in git(*log_args).split("\n")
                     if l.startswith("+") and not l.startswith("+++"))

ap = argparse.ArgumentParser()
ap.add_argument("--staged", action="store_true", help="스테이지에 올라간 것만 본다 (pre-commit 훅)")
ap.add_argument("--msg-file", default=None, help="커밋 메시지 파일 (commit-msg 훅)")
ap.add_argument("--range", default=None, help="검사할 커밋 범위. 예: origin/main..HEAD (pre-push 훅)")
a = ap.parse_args()
if not git("rev-parse", "--is-inside-work-tree").strip():
    print("ERROR: git 저장소가 아닙니다", file=sys.stderr); sys.exit(2)

hits, scope = [], []

if a.staged:
    names = [f for f in git("diff", "--cached", "--name-only", "--diff-filter=ACR").split("\n") if f]
    for f in names:
        if BAD_NAME.search(f): hits.append((f, 0, "올리면 안 되는 파일", f.split("/")[-1], ""))
    scan_text("스테이지에 올린 줄", added_lines("diff", "--cached", "-U0"), hits)
    scope.append(f"스테이지에 새로 올린 파일 {len(names)}개 · 바뀐 줄 전부")

if a.msg_file:
    mf = pathlib.Path(a.msg_file)
    if not mf.exists(): print(f"ERROR: 메시지 파일이 없습니다: {mf}", file=sys.stderr); sys.exit(2)
    # 주석 줄(#)은 커밋에 안 들어간다
    body = "\n".join(l for l in mf.read_text(encoding="utf-8").split("\n") if not l.startswith("#"))
    scan_text("커밋 메시지", body, hits)
    scope.append("커밋 메시지")

if a.range:
    for sha in [s for s in git("log", "--format=%H", a.range).split("\n") if s]:
        scan_text(f"커밋 {sha[:7]} 메시지", git("log", "-1", "--format=%B", sha), hits)
    scan_text(f"커밋 diff({a.range})", added_lines("log", "-p", "--format=", a.range), hits)
    n = len([s for s in git("log", "--format=%H", a.range).split("\n") if s])
    scope.append(f"커밋 {n}개 ({a.range})")

if not (a.staged or a.msg_file or a.range):        # 기본 — 지금 추적 중인 것 전부
    files = [f for f in git("ls-files").split("\n") if f]
    for f in files:
        if BAD_NAME.search(f): hits.append((f, 0, "올리면 안 되는 파일", f.split("/")[-1], ""))
        p = pathlib.Path(f)
        if not p.exists(): continue
        try: scan_text(f, p.read_text(encoding="utf-8"), hits)
        except (UnicodeDecodeError, OSError): continue
    scope.append(f"추적 파일 {len(files)}개")

if hits:
    print(f"개인 자산 검사 실패 — {len(hits)}건", file=sys.stderr)
    for where, line_no, what, found, ctx in hits:
        print(f"  {where}{':' + str(line_no) if line_no else ''}  [{what}] {found}" + (f"   {ctx}" if ctx else ""),
              file=sys.stderr)
    print("\n  이 저장소는 공개입니다. 지우고 다시 하세요.\n"
          "  이미 올라간 히스토리를 고치는 것은 되돌릴 수 없으니 사용자에게 물으세요.\n"
          "  검사가 잘못 잡은 것이라면 pipeline/check_private.py 의 예외를 고쳐야 합니다(엔지니어).", file=sys.stderr)
    sys.exit(3)
print(f"개인 자산 검사: {' · '.join(scope)} · 걸린 것 0건" + (f" · 기기 이름 {len(MACHINE)}개 대조" if MACHINE else ""))
