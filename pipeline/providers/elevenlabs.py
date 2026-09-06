"""ElevenLabs Text to Speech.

화자 고정은 voice_id 로 한다 — 같은 voice_id 면 항상 같은 목소리다.
본인 목소리를 쓰려면 ElevenLabs 에서 Voice Clone 을 만들고 그 voice_id 를 넣는다.
API 키는 환경변수로 둔다 (voice.json 에 키를 적지 말 것).
"""
import json, os, time, urllib.request

def generate(text, out_path, cfg, attempt=0):
    key = os.environ.get(cfg.get("api_key_env", "ELEVENLABS_API_KEY"))
    if not key:
        raise SystemExit(f"환경변수 {cfg.get('api_key_env','ELEVENLABS_API_KEY')} 가 비어 있습니다.")
    body = {
        "text": text,
        "model_id": cfg.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": cfg.get("stability", 0.5),
            "similarity_boost": cfg.get("similarity_boost", 0.8),
            "style": cfg.get("style", 0.0),
            "use_speaker_boost": cfg.get("use_speaker_boost", True),
        },
    }
    seeds = [cfg.get("seed")] + list(cfg.get("retry_seeds", []))
    seed = seeds[min(attempt, len(seeds) - 1)]
    if seed is not None:
        body["seed"] = int(seed)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['voice_id']}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=cfg.get("timeout_sec", 180)) as r:
        open(out_path, "wb").write(r.read())
    return round(time.time() - t0, 1)
