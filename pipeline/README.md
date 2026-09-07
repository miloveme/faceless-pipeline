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
| 10 | `10_tts_prep.py` | `script/scenes_v1.json` | `narration_tts` 필드, `audio/narration_tts_input.json` | 사전에 없는 영문 남으면 exit 2 |
| 15 | `15_clip_prep.py` | `source/` 의 영상·이미지, `script/visual_prep.json` | `public/<slug>/` 클립·이미지·스틸·컨택트 시트 | 소재 출처는 [VISUALS](../docs/VISUALS.md) |
| 18 | `18_bgm_prep.sh EP bgm.mp3` | BGM 원본 | `public/<slug>/bgm_lofi.mp3` (-27 LUFS) | |
| 20 | `20_tts_generate.py [--ids] [--seed] [--host] [--serial]` | tts_input, `voice.json` | `audio/nar_raw/<id>.mp3` | 서버 여러 대면 나눠서 동시에 |
| 30 | `30_nar_check.py [--ids]` | nar_raw | `whisper_cer.json`, `speech_bounds.json` | BAD 씬 있으면 exit 3 |
| 35 | `35_nar_retry.py --ids` | BAD 씬 | 시드 순회 교체 | 교체 후 30 재실행 |
| 40 | `40_nar_finalize.py` | nar_raw + bounds | `narration_final/*.wav`, `script/scenes_v2.json` | 트랙을 사람이 들음 |
| 45 | `45_visual_plan.py [--force]` | scenes_v2, scenes_v1 | `script/visual_plan.md` | 카드·이유는 사람이 채우고 승인 |
| 50 | `50_captions_build.py` | narration_final | `captions.json` | 자막 텍스트는 원문 |
| 55 | `55_remotion_sync.py [--skip-src-check]` | scenes_v2, captions | Remotion `public/`·`src/<slug>/data/` | 소재 경로가 `asset()` 을 지나는가·`SLUG` 가 이 편인가 → exit 3 |
| 60 | `60_render_master.sh EP Comp vX` | 컴포지션 | `edit/*_master.mp4` + 720p 프리뷰 | 사람이 프리뷰 검수 |
| 65 | `65_render_derived.sh EP` | Thumb/Shorts 컴포지션 | 썸네일·쇼츠 | |
| 70 | `70_srt_build.py` | captions(+captions_en) | `edit/*_ko.srt`, `*_en.srt` | |
| 75 | `75_chapters.py` | `script/chapters.json` | `edit/chapters.txt` | |
| 80 | `80_whiteboard_srt.py --ids` | scenes_v2, captions | 구간 SRT | 손그림 애니메이션용(선택) |

보조: `voice_similarity.py <참조> <생성물...>` — 화자 유사도 비교(librosa 필요).

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
- whisper 오타 사전 `whisper_fixes.json` + `<EP>/script/whisper_fixes.json`. 3자 이하 차이는 무시합니다.
- 꼬리 잡음은 30단계가 실제 끝을 제안하고 40단계가 적용합니다. 다르면 `<EP>/audio/bounds_override.json`이 우선입니다.
- Remotion 위치는 `REMOTION_DIR` 환경변수, 없으면 저장소의 `remotion/`.
- 컴포지션 이름 규약: `<PREFIX>-Episode`, `<PREFIX>-Thumb-A/B/C`, `<PREFIX>-Shorts-1/2` (PREFIX = 에피소드 폴더명 앞부분).
- whisper는 로컬 CPU에서 돕니다. 17씬 기준 검사 4~6분, 자막 4~6분. 백그라운드로 돌리세요.
