#!/usr/bin/env python3
"""올리기 전 개인 자산 검사. 이 저장소는 공개다 — 한 번 올라가면 지워도 남는다.

두 가지를 본다.
1. 추적 중인 파일 — 미디어·목소리 설정·에피소드 산출물이 섞여 있나 (.gitignore 는 이미 추적된 파일을 못 막는다)
2. 올릴 내용 — 파일 내용과 커밋 메시지에 개인 경로·사설 IP·이메일·MAC 이 있나

찾은 것이 있으면 종료코드 3. 없으면 0.
사용: check_private.py [--range origin/main..HEAD]   (범위를 안 주면 추적 파일 전체만 본다)
"""
import argparse, re, subprocess, sys, pathlib

def git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout

# 이름만으로 걸러야 하는 것
BAD_NAME = re.compile(r"\.(mp3|wav|m4a|mp4|mov|avi|mkv|zip)$|(^|/)voice\.json$|^episodes/|^assets/(?!README\.md$)")
# 내용에서 찾는 것. 문서 전용 IP 대역(RFC 5737)과 루프백은 뺀다 — 예시로 쓰라고 있는 값이다
DOC_IP = re.compile(r"^(127\.|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)")
# 커밋 트레일러의 noreply 주소는 사람 주소가 아니다
OK_MAIL = re.compile(r"^noreply@|@users\.noreply\.github\.com$|^[a-z]+@example\.(com|org)$")
PATTERNS = [
    ("개인 경로",  re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/")),
    ("사설 IP",    re.compile(r"(?<![\d.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}")),
    ("이메일",     re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("MAC 주소",   re.compile(r"(?<![:\w])(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}(?![:\w])")),
]

def scan_text(label, text, hits):
    for line_no, line in enumerate(text.split("\n"), 1):
        for what, pat in PATTERNS:
            for m in pat.finditer(line):
                if what == "사설 IP" and DOC_IP.match(m.group(0)): continue
                if what == "이메일" and OK_MAIL.search(m.group(0)): continue
                hits.append((label, line_no, what, m.group(0), line.strip()[:100]))

ap = argparse.ArgumentParser()
ap.add_argument("--range", default=None, help="검사할 커밋 범위. 예: origin/main..HEAD")
a = ap.parse_args()
if not git("rev-parse", "--is-inside-work-tree").strip():
    print("ERROR: git 저장소가 아닙니다", file=sys.stderr); sys.exit(2)

hits, files = [], [f for f in git("ls-files").split("\n") if f]
named = [f for f in files if BAD_NAME.search(f)]
for f in named:
    hits.append((f, 0, "올리면 안 되는 파일", f.split("/")[-1], ""))

for f in files:                                   # 텍스트 파일 내용
    p = pathlib.Path(f)
    if not p.exists(): continue
    try: scan_text(f, p.read_text(encoding="utf-8"), hits)
    except (UnicodeDecodeError, OSError): continue

if a.range:                                       # 올릴 커밋 — 메시지와 추가된 줄 (author 헤더는 git 신원이라 뺀다)
    for sha in [s for s in git("log", "--format=%H", a.range).split("\n") if s]:
        scan_text(f"커밋 {sha[:7]} 메시지", git("log", "-1", "--format=%B", sha), hits)
    # 범위 안에서 한 번이라도 들어간 줄. 나중에 지워도 히스토리에는 남는다
    added = "\n".join(l[1:] for l in git("log", "-p", "--format=", a.range).split("\n")
                       if l.startswith("+") and not l.startswith("+++"))
    scan_text(f"커밋 diff({a.range})", added, hits)

if hits:
    print(f"개인 자산 검사 실패 — {len(hits)}건")
    for where, line_no, what, found, ctx in hits:
        print(f"  {where}{':' + str(line_no) if line_no else ''}  [{what}] {found}" + (f"   {ctx}" if ctx else ""))
    print("\n  올리기 전에 지우세요. 이미 올라간 히스토리를 고치는 것은 되돌릴 수 없으니 사용자에게 물으세요.")
    sys.exit(3)
print(f"개인 자산 검사: 추적 파일 {len(files)}개 · 걸린 것 0건" + (f" · 커밋 범위 {a.range}" if a.range else ""))
