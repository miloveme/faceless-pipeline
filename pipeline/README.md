# 공정 스크립트

모든 스크립트는 에피소드 폴더 하나를 인자로 받습니다.
**이름만 주면 됩니다** — `00_new_episode.sh` 가 만든 곳(`episodes/`, `EPISODES_DIR` 로 옮길 수 있음)에서 찾습니다.
경로로 줘도 됩니다(`episodes/E01_myepisode`, 절대경로, 현재 폴더 기준 상대경로).

```bash
python3 pipeline/40_nar_finalize.py E01_myepisode
```

번호 순서가 실행 순서입니다. 무엇을 언제 돌리는지는 `skills/knowhow-episode/SKILL.md`(런북)가 정합니다.

| 번호 | 스크립트 | 입력 | 출력 | 게이트 |
|---|---|---|---|---|
| 00 | `00_new_episode.sh E01_slug "제목"` | — | 에피소드 폴더 골격 + 템플릿 | |
| 01 | `01_status.py [<EP>]` | — | 서버 연결·큐·남은 작업·예상 시간 | **작업 전 먼저** |
| 05 | `05_script_to_scenes.py [--md] [--renumber] [--force]` | 가장 최신 `script/script_v<N>.md` ([형식](../docs/SCRIPT_FORMAT.md)) | `script/scenes_v1.json` | 씬 번호·`[N]` 누락 검사, 옛 판본이면 exit 2 |
| 10 | `10_tts_prep.py [--ids]` | `script/scenes_v1.json` | `narration_tts` 필드, `audio/narration_tts_input.json`(무엇을 무엇으로 바꿨는지 `subs` 포함) | 소리로 못 내는 것(영문·기호)이 남으면 exit 2 |
| 15 | `15_clip_prep.py` | `source/` 의 영상·이미지, `script/visual_prep.json` | `public/<slug>/` 클립·이미지·스틸·컨택트 시트 | 소재 출처는 [VISUALS](../docs/VISUALS.md) |
| 18 | `18_bgm_prep.sh EP bgm.mp3` | BGM 원본 | `public/<slug>/bgm_lofi.mp3` (-27 LUFS) | |
| 20 | `20_tts_generate.py [--ids] [--seed] [--host] [--serial]` | tts_input, `voice.json` | `audio/nar_raw/<id>.mp3` | 서버 여러 대면 나눠서 동시에 |
| 30 | `30_nar_check.py [--ids] [--quiet-text]` | nar_raw, tts_input 의 `subs` | `whisper_cer.json`, `speech_bounds.json` | 숫자 누락·CER>0.06·내용 차이면 BAD → exit 3 |
| 35 | `35_nar_retry.py --ids` | BAD 씬 | 시드 순회 교체 | 교체 후 30 재실행 |
| 40 | `40_nar_finalize.py` | nar_raw + bounds | `narration_final/*.wav`, `script/scenes_v2.json` | 트랙을 사람이 들음 |
| 45 | `45_visual_plan.py [--force]` | scenes_v2, scenes_v1 | `script/visual_plan.md` | 카드·이유는 사람이 채우고 승인 |
| 50 | `50_captions_build.py` | narration_final | `captions.json` | 자막 텍스트는 원문 |
| 55 | `55_remotion_sync.py [--skip-src-check]` | scenes_v2, captions, visual_prep | Remotion `public/`·`src/<slug>/data/` | 소재가 변환본보다 나중인가·`asset()` 을 지나는가·`SLUG` 가 이 편인가 → exit 3 |
| 60 | `60_render_master.sh EP Comp vX` | 컴포지션 | `edit/*_master.mp4` + 720p 프리뷰 | 사람이 프리뷰 검수 |
| 65 | `65_render_derived.sh EP` | Thumb/Shorts 컴포지션 | 썸네일·쇼츠 | |
| 70 | `70_srt_build.py` | captions(+captions_en) | `edit/*_ko.srt`, `*_en.srt` | |
| 75 | `75_chapters.py` | `script/chapters.json` | `edit/chapters.txt` | |
| 80 | `80_whiteboard_srt.py --ids` | scenes_v2, captions | 구간 SRT | 손그림 애니메이션용(선택) |

보조
- `voice_similarity.py <참조> <생성물...>` — 화자 유사도 비교(librosa 필요).
- `check_private.py [--staged] [--msg-file F] [--range A..B]` — 개인 자산이 저장소에 들어가는 것을 막는다.
  **사람이 기억해서 돌리는 검사가 아니다.** `.githooks/` 의 세 훅이 부른다.

  | 언제 | 무엇을 보나 |
  |---|---|
  | `pre-commit` | 스테이지에 올린 파일 이름과 추가된 줄 · **그 파일이 부르는 것이 저장소에 있는가**(`check_imports.py`) |
  | `commit-msg` | 커밋 메시지 — 남의 경로를 인용하다 새로 흘리는 자리다 |
  | `pre-push` | 원격에 없는 커밋 전부의 메시지와 추가된 줄 |

  찾는 것: 개인 경로(`/Users/`·`/home/`·`C:\Users\`), 사설 IP, 이메일, MAC, 이 기계의 이름,
  새로 추적되는 미디어·`voice.json`·`episodes/`·`assets/`. 걸리면 종료코드 3.
  **미디어 확장자 20종이 `.gitignore` 에 다 있는지도 본다.** 목록에서 하나 빠지면 그 종류가 조용히
  추적 대상이 된다 — `png` 가 실제로 빠져 있어서 `15_clip_prep` 이 만드는 **원본 프레임 PNG** 가
  커밋될 뻔했다. 이미지도 미디어다.
  `.gitignore` 는 **이미 추적 중인 파일을 막지 못하고**, 커밋 메시지는 아예 안 본다.

- `check_imports.py [--staged|<파일...>]` — 올리는 `.ts/.tsx` 의 상대경로 import 가 저장소에 있는지 본다.
  **없거나 `.gitignore` 가 막는 것을 부르면 종료코드 3** — 내 기계에서는 돌고 클론하면 컴파일이 안 되는 자리다.
  실제로 두 번 났다(부품 파일을 빼먹고 데이터만 올릴 뻔한 것, 무시되는 에피소드 폴더를 `Root.tsx` 가 부르게 될 뻔한 것).

  훅 연결(`core.hooksPath`)은 `check_setup.py` 가 한다 — 클론마다 한 번 필요하고, 안 돼 있으면 그 자리에서 해 준다.
  거짓 경보를 안 내는 것이 더 중요해서 예외를 둔다: 루프백 `127.x`, 문서 전용 대역
  `192.0.2.x`·`198.51.100.x`·`203.0.113.x`(RFC 5737), 커밋 트레일러의 `noreply@`.
  계정명 자체는 찾지 않는다(`jun` 이 `junk` 에 걸린다) — 계정명이 드러나는 자리는 경로라 경로 모양으로 잡는다.

## 종료코드

`0` 성공 / `2` 설정·인자 오류(사람이 고쳐야 함) / `3` 검사 실패(`46_grammar_check` 등) / `1` 그 밖의 실패.

**아직 전부 맞춰지지 않았습니다.** 에피소드 폴더를 못 찾으면 규약상 2 여야 하지만 지금은 1 입니다.
`set -e` 로 도는 60·65 단계의 동작이 바뀌는 변경이라, E01 을 끝내고 `pipeline/` 전체를 한 번에 맞춥니다.

호출부는 `| tail` 로 삼키지 말고 종료코드를 확인하세요.

## 규약
- 상수는 `common.py` 한 곳: LEAD 0.5 / GAP 0.8 / PAD 0.35 / 내레이션 -16 / 마스터 -14 / BGM -27 LUFS.
- 서버 선택은 `hosts.py` — `hosts` 순서대로, 막히면 다음, 여럿이면 동시에.
- 목소리 설정은 `pipeline/voice.json` (`voice.example.json`을 복사해 작성). 어느 서비스로 만들지는 `provider` 가 정하고 어댑터는 `providers/` 에 있습니다 → `docs/VOICE_PROVIDERS.md`. 재시도는 시드만 바꿉니다.
- 읽기 사전 `tts_readings.json`(공통) + `<EP>/script/tts_overrides.json`(에피소드별).
- **소수는 자릿수를 띄어 읽습니다** — `9.167` → `구 점 일 육 칠`. 붙여 쓰면 자음동화로 자릿수가 무너집니다
  (`일육`[일륙] → [이륙] → `9.267`, E01 실측). 정수부는 자릿값 읽기라 안 띄웁니다.
- **10단계를 통과하는 글자는 한글·숫자·공백·`.` `,` `?` `!` 뿐입니다.** 그 밖의 것이 남으면 멈춥니다 —
  기호를 사전으로 하나씩 막으면 다음 편에서 `%`·`±`·`→`·괄호가 같은 구멍으로 지나갑니다.
  숫자 사이의 `~`·`-` 는 `에서`, 줄표 `—` 는 쉼표로 바뀝니다(숫자 **앞**의 `-` 는 그대로 마이너스).
- **소재를 바꾸면 15단계를 다시 돌립니다.** 안 돌리면 렌더에 **옛 그림이 멀쩡하게** 나옵니다 —
  화면이 안 깨지므로 사람 눈에 안 걸립니다. 55단계가 `source/` 와 `public/<slug>/` 의 시각을 대조해
  뒤처진 것이 있으면 멈춥니다(exit 3). 남이 소재를 바꿨을 때가 특히 놓치기 쉽습니다.
- **숫자는 CER 과 별개로 완전일치로 봅니다.** 118자 문장에서 한 글자는 CER 0.013 이라 문턱을 낮춰도
  못 잡고, 그만큼 조이면 정상 씬(최대 0.054 실측)이 먼저 걸립니다. 10단계가 남긴 `subs` 의 숫자 읽기가
  받아쓰기에 그대로 있는지 30단계가 대조합니다.
  - 대조하는 것은 **숫자에서 온 부분(`subs[].num`)만**입니다. 뒤에 붙은 단위·조사까지 묶으면
    `초` 가 `추` 로 들린 것 같은 뒤 글자 오독이 숫자 오독으로 잡힙니다(E01 s15). 그쪽은 CER 과 `big_diffs` 가 봅니다.
  - **대본에 나온 순서대로** 찾습니다. `영` 처럼 한 글자짜리 읽기가 앞쪽 다른 숫자(`십 점 영 사`)의
    일부에 걸려 통과하는 것을 막습니다(E01 s09).
- **`0` 은 한자어로 읽습니다** — `0개` → `영 개`. 고유어 수사에 0 이 없어 그냥 두면 숫자가 통째로
  사라집니다(`0개` → ` 개`). 1 이상은 그대로 고유어입니다(`1개` → `한 개`).
- whisper 오타 사전 `whisper_fixes.json` + `<EP>/script/whisper_fixes.json`. 3자 이하 차이는 무시합니다.
- 꼬리 잡음은 30단계가 실제 끝을 제안하고 40단계가 적용합니다. 다르면 `<EP>/audio/bounds_override.json`이 우선입니다.
- Remotion 위치는 `REMOTION_DIR` 환경변수, 없으면 저장소의 `remotion/`.
- 컴포지션 이름 규약: `<PREFIX>-Episode`, `<PREFIX>-Thumb-A/B/C`, `<PREFIX>-Shorts-1/2` (PREFIX = 에피소드 폴더명 앞부분).
- whisper는 로컬 CPU에서 돕니다. 17씬 기준 검사 4~6분, 자막 4~6분. 백그라운드로 돌리세요.
