#!/bin/bash
# 새 에피소드 폴더 골격. 사용: 00_new_episode.sh E01_myepisode "제목(가제)"
set -e
set -o pipefail
NAME=$1; TITLE=${2:-"(가제)"}; ROOT=$(cd "$(dirname "$0")/.." && pwd); EP=${EPISODES_DIR:-$ROOT/episodes}/$NAME
[ -z "$NAME" ] && { echo "사용: 00_new_episode.sh E01_myepisode \"제목\""; exit 1; }
[ -e "$EP" ] && { echo "이미 있음: $EP"; exit 1; }
mkdir -p "$(dirname "$EP")"
mkdir -p "$EP"/{source,script,audio,edit}
cat > "$EP/STATUS.md" <<EOT
# $NAME — $TITLE
상태: 0 주제선정 ☐ → 1 대본 ☐(게이트) → 2 내레이션 ☐ → 3 템플릿 ☐(게이트) → 4 조립·파생 ☐ → 5 업로드 ☐(게이트)
출처 프로젝트:
원본 클립(실패/성공):
모델 표기(생성 기록 확인):
결정 사항:
EOT
cat > "$EP/source/SOURCES.md" <<'EOT'
# 소재 출처

이 편의 화면 소재를 여기에 적습니다. 파일만 있으면 몇 주 뒤에 어디서 왔는지 모르게 됩니다.
설명란에 사용 모델을 밝힐 때도 이 기록을 씁니다. → docs/VISUALS.md

| 파일 | 종류 | 어디서 왔나 | 날짜 | 비고 |
|---|---|---|---|---|
|  | existing / record / gen-video / gen-image / whiteboard |  |  |  |

## AI 로 만든 것

모델과 프롬프트를 남깁니다. 같은 톤으로 하나 더 만들어야 할 때 필요합니다.

```
파일:
모델:
프롬프트:
참조 이미지:
```
EOT
cat > "$EP/source/README.md" <<'EOT'
이 편에서만 쓰는 소재를 여기에 둡니다. 원본을 옮기지 말고 복사해 오세요.
여러 편에서 쓰는 것은 저장소 루트의 assets/ 로 갑니다.
출처는 SOURCES.md 에 적습니다. 넣는 법은 docs/VISUALS.md.
EOT
cat > "$EP/script/script_v1.md" <<'EOT'
# 제목을 여기에

<!-- 형식 설명: docs/SCRIPT_FORMAT.md
     ## s<번호> <씬 제목>
     [V] 화면에 무엇을 띄울지 (자기 자신에게 남기는 지시)
     [N] 실제로 읽을 문장 (이 글자가 음성이 되고 자막이 된다)
     다 쓰면: python3 pipeline/05_script_to_scenes.py <EP> -->

## s00 훅
[V] 결과물이나 증상을 바로 보여준다
[N] 첫 문장. 무엇을 볼지, 왜 봐야 하는지 짧게.

## s01 증상
[V] 무엇이 잘못됐는지 화면으로
[N]

## s02 흔한 오답
[V]
[N]

## s03 진짜 원인
[V]
[N]

## s04 처방
[V]
[N]

## s05 검증
[V] 전후 비교
[N]

## s06 규칙 한 줄
[V] 텍스트 카드
[N]

## s07 마무리
[V] 텍스트 카드
[N] 도움이 됐다면 구독과 좋아요 부탁드립니다.

## 미결
- 확인이 필요한 것을 여기에. 이 절은 씬으로 읽히지 않는다.
EOT
echo '{}' > "$EP/script/tts_overrides.json"
echo '[["s00","실패 테이크"]]' > "$EP/script/chapters.json"
echo '{"clips":{},"stills":{},"contact":[]}' > "$EP/script/visual_prep.json"
echo "created $EP"; find "$EP" -type f | sort
