"""OpenAI Text to Speech.

화자 고정은 voice 이름으로 한다(alloy, echo, onyx, nova, shimmer 등).
목소리를 복제할 수는 없고 제공되는 목소리 중에서 고른다.
시드가 없어 재시도는 그냥 다시 생성한다.
"""
import json, os, time, urllib.request

def generate(text, out_path, cfg, attempt=0):
    key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"))
    if not key:
        raise SystemExit(f"환경변수 {cfg.get('api_key_env','OPENAI_API_KEY')} 가 비어 있습니다.")
    body = {"model": cfg.get("model", "gpt-4o-mini-tts"), "voice": cfg.get("voice", "onyx"),
            "input": text, "response_format": cfg.get("format", "mp3")}
    if cfg.get("instructions"):
        body["instructions"] = cfg["instructions"]     # 톤 지시 (지원 모델만)
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=cfg.get("timeout_sec", 180)) as r:
        open(out_path, "wb").write(r.read())
    return round(time.time() - t0, 1)
