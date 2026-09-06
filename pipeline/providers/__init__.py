"""음성 제공자 어댑터.

각 모듈은 함수 하나만 노출한다:

    generate(text, out_path, cfg, attempt=0) -> float | None
        text     : 읽을 문장 (전처리 끝난 것)
        out_path : 저장할 경로 (.mp3 또는 .wav)
        cfg      : voice.json 의 providers[<이름>] 블록
        attempt  : 0=첫 시도, 1,2,...=재시도. 시드를 지원하면 여기서 바꾼다.
        반환      : 생성에 걸린 초 (모르면 None)

새 제공자를 붙이려면 이 폴더에 파일 하나를 만들고 REGISTRY 에 등록하면 된다.
어느 것을 쓸지는 voice.json 의 "provider" 가 정한다.
"""
import importlib

REGISTRY = {
    "comfyui_chatterbox": "comfyui_chatterbox",   # 자체 호스팅 ComfyUI + Chatterbox 노드 (검증됨)
    "elevenlabs": "elevenlabs",                   # ElevenLabs REST API
    "openai": "openai_tts",                       # OpenAI TTS REST API
    "shell": "shell",                             # 임의의 외부 명령 (무엇이든 붙일 수 있는 탈출구)
}

def get(name):
    if name not in REGISTRY:
        raise SystemExit(f"모르는 제공자: {name}. 가능한 값: {', '.join(REGISTRY)}")
    return importlib.import_module(f"providers.{REGISTRY[name]}")
