"""외부 명령으로 음성을 만든다 — 무엇이든 붙일 수 있는 탈출구.

여기 없는 서비스(Higgsfield, fal, MiniMax, Fish, 자체 모델 등)를 쓰고 싶으면
텍스트를 받아 오디오 파일을 만드는 스크립트를 하나 짜고 그 경로를 적으면 된다.

cfg:
  command  : 실행할 명령. 치환자 {text_file} {out} {attempt} 를 쓴다.
  timeout_sec

예)
  "command": "python3 my_tts.py --in {text_file} --out {out} --attempt {attempt}"

텍스트는 파일로 넘긴다(따옴표·줄바꿈 문제를 피하기 위해). 명령은 셸을 거치지 않고
인자 배열로 실행되므로 셸 문법(파이프, 리다이렉트)은 쓸 수 없다.
"""
import pathlib, shlex, subprocess, tempfile, time

def generate(text, out_path, cfg, attempt=0):
    if "command" not in cfg:
        raise SystemExit("shell 제공자에는 command 가 필요합니다.")
    tf = pathlib.Path(tempfile.mkdtemp()) / "line.txt"
    tf.write_text(text, encoding="utf-8")
    argv = [a.replace("{text_file}", str(tf)).replace("{out}", str(out_path))
             .replace("{attempt}", str(attempt)) for a in shlex.split(cfg["command"])]
    t0 = time.time()
    p = subprocess.run(argv, capture_output=True, text=True, timeout=cfg.get("timeout_sec", 600))
    if p.returncode != 0:
        raise RuntimeError(f"명령 실패 (코드 {p.returncode})\n{p.stderr[-800:]}")
    if not pathlib.Path(out_path).exists() or pathlib.Path(out_path).stat().st_size == 0:
        raise RuntimeError(f"명령은 성공했지만 파일이 없습니다: {out_path}")
    return round(time.time() - t0, 1)
