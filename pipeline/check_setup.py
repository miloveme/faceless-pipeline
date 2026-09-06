#!/usr/bin/env python3
"""설치 점검. 무엇이 준비됐고 무엇이 빠졌는지 알려준다."""
import importlib, json, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
ok = True
def line(name, good, note=""):
    global ok
    print(f"  {'ok ' if good else 'X  '}{name:28}{note}")
    if not good: ok = False

print("파이썬 패키지")
for m, why in [("whisper","내레이션 검사·자막 타이밍"),("numpy",""),("scipy",""),
               ("PIL","컨택트 시트"),("librosa","화자 유사도(선택)")]:
    try: importlib.import_module(m); line(m, True, why)
    except Exception: line(m, m=="librosa", ("선택 — " if m=="librosa" else "pip install -r requirements.txt  ")+why)

print("\n시스템 도구")
for c, why in [("ffmpeg","오디오·영상"),("ffprobe","길이 측정"),("node","Remotion"),("npx","Remotion")]:
    line(c, shutil.which(c) is not None, why)

print("\nRemotion")
rd = pathlib.Path(__import__("os").environ.get("REMOTION_DIR", ROOT/"remotion"))
line("프로젝트 폴더", rd.is_dir(), str(rd))
line("node_modules", (rd/"node_modules").is_dir(), "없으면: cd remotion && npm install")
line("공용 컴포넌트", (rd/"src"/"knowhow").is_dir(), str(rd/"src"/"knowhow"))

print("\n목소리 설정")
vj = ROOT/"pipeline"/"voice.json"
line("voice.json", vj.exists(), "없으면: cp pipeline/voice.example.json pipeline/voice.json")
if vj.exists():
    v = json.load(open(vj))
    host = v.get("host","")
    line("host 설정", "<" not in host and host.startswith("http"), host or "(비어 있음)")
    ref = ROOT/"pipeline"/v.get("ref_file","")
    line("참조 음성", ref.exists(), f"{v.get('ref_file')} — docs/RECORDING.md 참고")
    if host.startswith("http"):
        import socket, urllib.parse
        u = urllib.parse.urlparse(host)
        try:
            socket.create_connection((u.hostname, u.port or 8188), timeout=3).close(); reach = True
        except Exception: reach = False
        line("ComfyUI 연결", reach, f"{u.hostname}:{u.port or 8188}")

print("\n" + ("전부 준비됐습니다." if ok else "위의 X 항목을 해결한 뒤 다시 실행하세요."))
sys.exit(0 if ok else 1)
