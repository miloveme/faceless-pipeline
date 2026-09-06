# faceless-pipeline

내레이션 기반 faceless 영상을 **한 편씩 반복 가능하게** 만드는 공정입니다.
대본을 씬 단위 데이터로 쓰면, 음성 생성부터 검사·트리밍·시각표·자막·렌더·썸네일·쇼츠까지 명령으로 이어집니다.
사람은 세 곳에서만 멈춰 판단합니다. **대본 / 화면 첫 렌더 / 업로드**.

## 무엇이 들어 있나

```
pipeline/    번호순 공정 스크립트 (00 → 80)
assets/      여러 편에서 쓰는 자산 (로고·생성 참조·BGM)
episodes/    편별 작업 폴더 (소재·대본·음성·결과물)
skills/      제작 런북 (Claude Code 스킬 형식)
remotion/    화면 컴포넌트 + 에피소드 템플릿
docs/        목소리 준비·녹음 가이드
```

## 준비물

| 항목 | 용도 | 비용 |
|---|---|---|
| Python 3.10+ | 공정 스크립트 | 무료 |
| ffmpeg | 오디오·영상 처리 | 무료 |
| Node 18+ | Remotion 렌더 | 무료 |
| Whisper (로컬) | 내레이션 검사·자막 타이밍 | 무료 |
| 음성 서비스 (택1) | 내레이션 생성 | 자체 호스팅이면 무료 |

선택 사항으로 손그림 애니메이션 도구가 있습니다 — [srt-whiteboard-animation](https://github.com/miloveme/srt-whiteboard-animation).
개념 설명 구간에만 쓰므로 필요할 때 설치하면 됩니다(`bash pipeline/install_whiteboard.sh`).

음성은 **여러 서비스 중에서 고릅니다**. 자체 호스팅 ComfyUI(Chatterbox), ElevenLabs, OpenAI 가 기본으로 들어 있고,
그 밖의 서비스는 `shell` 제공자로 스크립트 하나만 짜면 붙습니다. 고르고 바꾸는 법은 [docs/VOICE_PROVIDERS.md](docs/VOICE_PROVIDERS.md).

## 설치

```bash
git clone <이 저장소> faceless-pipeline
cd faceless-pipeline

# 1) 파이썬 의존성
python3 -m pip install -r requirements.txt

# 2) 시스템 도구 (macOS 기준)
brew install ffmpeg node

# 3) Remotion
cd remotion && npm install && cd ..

# 4) 목소리 설정 — provider 를 고르고 그 블록만 채운다
cp pipeline/voice.example.json pipeline/voice.json
#   docs/VOICE_PROVIDERS.md 참고. 본인 목소리로 하려면 docs/RECORDING.md

# 5) 점검
python3 pipeline/check_setup.py
```

## 첫 한 편 만들기

```bash
# 에피소드 폴더 만들기
bash pipeline/00_new_episode.sh E01_myepisode "첫 편 제목"

# script/script_v1.md 에 대본을 쓴다 (사람 몫 — 아래 형식)
#   형식은 docs/SCRIPT_FORMAT.md — ## s00 / [V] 화면 / [N] 읽을 문장

python3 pipeline/05_script_to_scenes.py episodes/E01_myepisode  # 대본 → 씬 JSON
python3 pipeline/10_tts_prep.py episodes/E01_myepisode   # 숫자·영문 읽기 전처리
python3 pipeline/20_tts_generate.py episodes/E01_myepisode
python3 pipeline/30_nar_check.py episodes/E01_myepisode  # 문장 누락·꼬리 잡음 검사
python3 pipeline/40_nar_finalize.py episodes/E01_myepisode  # 트림·정규화·시각표
python3 pipeline/50_captions_build.py episodes/E01_myepisode
python3 pipeline/55_remotion_sync.py episodes/E01_myepisode
bash    pipeline/60_render_master.sh episodes/E01_myepisode E01-Episode v1
bash    pipeline/65_render_derived.sh episodes/E01_myepisode
python3 pipeline/70_srt_build.py episodes/E01_myepisode
python3 pipeline/75_chapters.py episodes/E01_myepisode
```

### 문서
- [대본 형식](docs/SCRIPT_FORMAT.md) — `[V]` `[N]` 태그와 규칙
- [화면 디자인](docs/DESIGN.md) — 색·글꼴·여백을 바꾸는 곳, 카드 고치는 곳
- [화면 소재](docs/VISUALS.md) — 녹화·AI 생성·손그림·기존 자산을 넣는 법
- [음성 제공자](docs/VOICE_PROVIDERS.md) — 서비스 고르기·바꾸기
- [목소리 준비](docs/RECORDING.md) — 본인 목소리 녹음과 클론
- [제작 런북](skills/knowhow-episode/SKILL.md) — 단계별 판단 기준

단계별 입출력과 통과 기준은 [pipeline/README.md](pipeline/README.md), 언제 무엇을 돌릴지는 [런북](skills/knowhow-episode/SKILL.md)에 있습니다.

## 설계에서 지킨 것

- **대본은 마크다운으로, 공정은 JSON으로.** 사람은 읽고 고치기 쉬운 형식으로 쓰고, 변환은 스크립트가 합니다.
- **음성 길이가 영상 길이를 정한다.** 화면에 맞춰 음성을 늘이지 않습니다. 음성을 재서 시각표를 만듭니다.
- **생성물을 믿지 않는다.** 만든 음성을 받아쓰기에 넣어 원본과 글자 단위로 비교합니다.
- **검사기도 틀린다.** 받아쓰기가 자주 틀리는 단어는 사전으로 거르고, 꼬리에 붙은 문장과 중간에 빠진 문장을 구분합니다. 앞은 잘라내면 되고 뒤는 다시 만들어야 합니다.
- **재시도는 시드만 바꾼다.** 설정을 건드리면 목소리가 달라집니다.
- **음성 서비스는 갈아 끼운다.** 검사·트리밍·시각표·자막·렌더는 음성이 어디서 왔는지 모릅니다.
- **규칙은 문서가 아니라 스크립트에.** 문장으로 적어 둔 규칙은 잊히지만, 공정 안에 있으면 어길 수가 없습니다.
- **자막은 원문으로, 타이밍만 받아쓰기로.** 받아쓰기를 그대로 쓰면 오타가 화면에 박힙니다.

## Claude Code로 쓸 때

저장소 루트의 `CLAUDE.md`가 자동으로 읽힙니다. 런북을 스킬로 쓰려면:

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/knowhow-episode" ~/.claude/skills/knowhow-episode
```

## 라이선스

MIT
