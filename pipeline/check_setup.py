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

print("\n저장소 훅 — 개인 자산이 커밋·푸시에 섞이는 것을 막는다")
hooks = ROOT/".githooks"
if (ROOT/".git").exists() and hooks.is_dir():
    cur = subprocess.run(["git","-C",str(ROOT),"config","--get","core.hooksPath"],
                         capture_output=True, text=True).stdout.strip()
    if cur != ".githooks":
        # 이 설정은 이 클론에만 걸린다. 사람이 기억해서 켜야 하는 검사는 안 걸리므로 여기서 연결한다.
        subprocess.run(["git","-C",str(ROOT),"config","core.hooksPath",".githooks"], capture_output=True)
        cur = subprocess.run(["git","-C",str(ROOT),"config","--get","core.hooksPath"],
                             capture_output=True, text=True).stdout.strip()
        line("core.hooksPath", cur == ".githooks", f"방금 연결했습니다 → {cur or '(실패)'}")
    else:
        line("core.hooksPath", True, ".githooks (pre-commit·commit-msg·pre-push)")
    line("check_private.py", (ROOT/"pipeline"/"check_private.py").exists(), "훅이 부르는 검사")
else:
    line("core.hooksPath", True, "git 저장소가 아니거나 .githooks 가 없습니다 — 건너뜀")

print("\nRemotion")
rd = pathlib.Path(__import__("os").environ.get("REMOTION_DIR", ROOT/"remotion"))
line("프로젝트 폴더", rd.is_dir(), str(rd))
line("node_modules", (rd/"node_modules").is_dir(), "없으면: cd remotion && npm install")
line("공용 컴포넌트", (rd/"src"/"knowhow").is_dir(), str(rd/"src"/"knowhow"))

print("\n선택 — 손그림 애니메이션")
wb = pathlib.Path(__import__("os").environ.get("WHITEBOARD_DIR", pathlib.Path.home()/".claude"/"skills"/"srt-whiteboard-animation"))
have_wb = (wb/"scripts"/"render_stream_whiteboard.py").exists()
line("srt-whiteboard-animation", True,
     str(wb) if have_wb else "선택 — 안 쓰면 무시. 설치: bash pipeline/install_whiteboard.sh")

print("\n목소리 설정")
vj = ROOT/"pipeline"/"voice.json"
line("voice.json", vj.exists(), "없으면: cp pipeline/voice.example.json pipeline/voice.json")
if vj.exists():
    v = json.load(open(vj))
    name = v.get("provider")
    blocks = v.get("providers") if isinstance(v.get("providers"), dict) else {}
    line("provider", bool(name) and name in blocks,
         f"{name or '(비어 있음)'} — providers 블록이 있어야 합니다")
    pv = blocks.get(name, {})
    host = (pv.get("hosts") or [pv.get("host","")])[0] if name == "comfyui_chatterbox" else ""
    if name == "comfyui_chatterbox":
        line("host 설정", "<" not in host and host.startswith("http"), host or "(비어 있음)")
        ref = ROOT/"pipeline"/pv.get("ref_file","")
        line("참조 음성", ref.exists(), f"{pv.get('ref_file')} — docs/RECORDING.md 참고")
    elif pv.get("api_key_env"):
        line("API 키 환경변수", bool(__import__("os").environ.get(pv["api_key_env"])),
             f"{pv['api_key_env']} — export {pv['api_key_env']}=...")
    if host.startswith("http"):
        import socket, urllib.parse
        u = urllib.parse.urlparse(host)
        try:
            socket.create_connection((u.hostname, u.port or 8188), timeout=3).close(); reach = True
        except Exception: reach = False
        line("ComfyUI 연결", reach, f"{u.hostname}:{u.port or 8188}" + ("" if reach else
             " — 서버가 꺼져 있거나 주소가 다릅니다"))
        if not reach:
            print("     주소는 사람마다 달라 저장소에 없습니다. 모르면 추측하지 말고 사용자에게 물어보세요.")
            print(f"     확인한 뒤 {vj} 의 providers.{name}.hosts 를 고칩니다.")

print("\n" + ("전부 준비됐습니다." if ok else "위의 X 항목을 해결한 뒤 다시 실행하세요."))
sys.exit(0 if ok else 1)
