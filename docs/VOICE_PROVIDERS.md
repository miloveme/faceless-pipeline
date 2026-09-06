# 음성 제공자 — 고르고 바꾸는 법

내레이션을 어느 서비스로 만들지는 `pipeline/voice.json` 의 `provider` 한 줄이 정합니다.
**바꿔도 나머지 공정은 그대로입니다.** 검사·트리밍·시각표·자막·렌더는 음성이 어디서 왔는지 모릅니다.

```bash
cp pipeline/voice.example.json pipeline/voice.json
# provider 를 원하는 값으로 바꾸고, 그 제공자 블록만 채우면 됩니다
python3 pipeline/check_setup.py     # 설정이 맞는지 점검
```

## 고르는 기준

가장 중요한 것은 **화자 일관성**입니다. 문단을 하나씩 따로 만들기 때문에, 매번 같은 사람이 읽어야 합니다.
서비스마다 이걸 보장하는 방식이 다릅니다.

| 제공자 | 화자 고정 방식 | 본인 목소리 | 비용 | 상태 |
|---|---|---|---|---|
| `comfyui_chatterbox` | 참조 음성 파일 | 가능 (녹음 30~60초) | 자체 GPU면 0 | 검증됨 |
| `elevenlabs` | voice_id | 가능 (Voice Clone) | 글자당 과금 | 문서 기반 |
| `openai` | voice 이름 | 불가 (제공 목소리 중 선택) | 글자당 과금 | 문서 기반 |
| `shell` | 직접 짠 스크립트에 달림 | 스크립트에 달림 | 서비스에 달림 | 탈출구 |

"검증됨"은 이 공정으로 실제 한 편을 끝까지 만들어 본 것, "문서 기반"은 각 서비스의 공개 API 문서대로 구현했지만 이 저장소에서 끝까지 돌려 보지는 않은 것입니다.

**절대 하면 안 되는 것**: 서비스의 기본 목소리를 화자 지정 없이 문단마다 호출하는 것. 호출할 때마다 다른 사람이 읽어서, 이어 붙이면 여러 명이 돌아가며 녹음한 영상이 됩니다.

## 제공자별 설정

### comfyui_chatterbox (자체 호스팅)
ComfyUI 에 Chatterbox 다국어 TTS 커스텀 노드를 설치해서 씁니다. 참조 음성 하나로 화자를 고정합니다.

```json
"provider": "comfyui_chatterbox",
"providers": { "comfyui_chatterbox": {
  "hosts": ["http://192.0.2.10:8188", "http://127.0.0.1:8188"],
  "max_queue": 2,
  "parallel": true,
  "ref_file": "channel_voice_ref.mp3",
  "seed": 163260306,
  "retry_seeds": [7, 99, 2024, 31337]
}}
```

**서버를 여러 대 쓸 수 있습니다.** `hosts` 는 우선순위 순서입니다.
- 앞의 것이 기본입니다. 응답이 없거나 큐가 `max_queue` 보다 길면 다음으로 넘어갑니다.
- 씬이 여러 개고 `parallel` 이 켜져 있으면 **살아 있는 서버에 나눠 동시에 돌립니다.**
- 한 대가 도중에 죽으면 그 씬은 다른 서버가 집어갑니다. 두 번 연속 실패한 서버는 뺍니다.
- 전부 바쁘면 가장 덜 바쁜 한 대에 맡깁니다. 기다리는 게 안 하는 것보다 낫습니다.
- 한 대만 쓰려면 `20_tts_generate.py <EP> --serial`, 특정 서버를 지정하려면 `--host <주소>`.

실측 참고: 같은 모델이라도 **음성 생성은 GPU 성능을 크게 타지 않습니다.**
Apple Silicon 통합 메모리와 RTX 3090 을 같은 문장으로 비교했을 때 처리량 차이가 3% 였습니다
(초당 8.3자 대 8.5자). 순차적으로 한 토큰씩 만드는 구조라 병렬 연산 이득이 적습니다.
그러니 좋은 GPU 는 영상 생성에 쓰고, 음성은 남는 기계에 돌리는 편이 낫습니다.
- 참조 음성은 `pipeline/` 안에 두고, **저장소에 커밋하지 마세요**(gitignore 에 있습니다).
- 참조 만드는 법은 [RECORDING.md](RECORDING.md).
- 로컬 GPU 가 없으면 클라우드 ComfyUI 주소를 `host` 에 넣으면 됩니다.

### elevenlabs
```json
"provider": "elevenlabs",
"providers": { "elevenlabs": {
  "api_key_env": "ELEVENLABS_API_KEY",
  "voice_id": "<voice_id>",
  "model_id": "eleven_multilingual_v2"
}}
```
```bash
export ELEVENLABS_API_KEY=...   # 키는 voice.json 이 아니라 환경변수에
```
- 본인 목소리를 쓰려면 ElevenLabs 에서 Voice Clone 을 만들고 그 `voice_id` 를 넣습니다.
- `stability` 를 높이면 안정적이지만 밋밋해지고, 낮추면 표현이 살지만 문단 간 편차가 커집니다.

### openai
```json
"provider": "openai",
"providers": { "openai": {
  "api_key_env": "OPENAI_API_KEY",
  "model": "gpt-4o-mini-tts",
  "voice": "onyx",
  "instructions": "차분하고 또박또박, 설명하는 톤"
}}
```
- 목소리 복제는 안 되고 제공되는 것 중에서 고릅니다. 대신 `instructions` 로 톤을 지시할 수 있습니다.
- 시드가 없어 재시도는 그냥 다시 생성합니다.

### shell (여기 없는 서비스 붙이기)
Higgsfield, fal, MiniMax, Fish 처럼 목록에 없는 서비스나 자체 모델은 이 방법으로 붙입니다.
텍스트 파일을 받아 오디오 파일을 만드는 스크립트를 하나 짜면 됩니다.

```json
"provider": "shell",
"providers": { "shell": {
  "command": "python3 my_tts.py --in {text_file} --out {out} --attempt {attempt}"
}}
```

치환자는 셋입니다. `{text_file}` 읽을 문장이 담긴 파일, `{out}` 저장할 경로, `{attempt}` 시도 번호(0=첫 시도).
스크립트가 할 일은 하나입니다. **문장을 읽어 `{out}` 에 오디오 파일을 만든다.**

```python
# my_tts.py 최소 예시
import argparse, pathlib, requests, os
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="i"); ap.add_argument("--out"); ap.add_argument("--attempt", default="0")
a = ap.parse_args()
text = pathlib.Path(a.i).read_text(encoding="utf-8")

r = requests.post("https://api.example.com/tts",
                  headers={"Authorization": f"Bearer {os.environ['MY_API_KEY']}"},
                  json={"text": text, "voice_id": "고정한_화자_id"}, timeout=180)
r.raise_for_status()
pathlib.Path(a.out).write_bytes(r.content)
```

`{attempt}` 를 받는 이유는 재시도 때문입니다. 검사에 걸린 씬을 다시 만들 때 시드나 온도를 조금 바꿀 수 있으면
여기서 반영하세요. **화자 설정은 절대 바꾸지 마세요** — 목소리가 달라집니다.

## 새 제공자를 코드로 추가하기

`shell` 로 충분하지만, 자주 쓴다면 어댑터를 만드는 편이 깔끔합니다.

1. `pipeline/providers/myservice.py` 를 만들고 함수 하나를 노출합니다.
   ```python
   def generate(text, out_path, cfg, attempt=0):
       ...
       return 걸린_초  # 모르면 None
   ```
2. `pipeline/providers/__init__.py` 의 `REGISTRY` 에 한 줄 추가합니다.
3. `voice.json` 의 `providers` 에 설정 블록을 넣고 `provider` 를 그 이름으로 바꿉니다.

## 바꾼 뒤 확인할 것

제공자를 바꾸면 목소리가 바뀝니다. 짧은 문장 두세 개로 먼저 시험하고 전체에 적용하세요.

```bash
python3 pipeline/20_tts_generate.py episodes/E01_x --ids s00,s01
python3 pipeline/30_nar_check.py    episodes/E01_x --ids s00,s01
```

- **읽기 검사**: 문장이 빠지거나 반복되지 않는지. 30단계가 잡아 줍니다.
- **화자 일관성**: 문단이 바뀌어도 같은 사람인지. 귀로 듣고, 필요하면 수치로 확인합니다.
  ```bash
  python3 pipeline/voice_similarity.py <참조_또는_첫씬> <나머지 씬들...>
  ```
  같은 화자면 음색 유사도 0.99 이상·음높이 차이 10Hz 이내, 다른 화자면 0.89 수준·60Hz 차이로 갈립니다.
- **길이**: 제공자마다 말 속도가 달라 전체 영상 길이가 달라집니다. 40단계가 시각표를 다시 계산하므로
  화면 쪽은 자동으로 맞지만, 편당 목표 길이가 있다면 확인하세요.

## 한 편 안에서 섞지 마세요

제공자를 바꾸면 그 이후 편의 목소리가 전부 바뀝니다. **한 편 안에서 제공자를 섞으면 문단마다 화자가 달라집니다.**
바꿀 때는 편 단위로 바꾸고, 바꾼 날짜를 기록해 두세요.

예외는 직접 녹음과의 병행입니다. 그건 [RECORDING.md](RECORDING.md) 를 보세요.
