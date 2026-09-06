#!/bin/bash
# 새 에피소드 폴더 골격. 사용: 00_new_episode.sh E01_myepisode "제목(가제)"
set -e
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
cat > "$EP/script/scenes_v1.json" <<EOT
{"episode":"$NAME","title":"$TITLE","scenes":[
 {"id":"s00","section":"hook","narration":"","visual":{"type":"clip","note":""}},
 {"id":"s01","section":"symptom","narration":"","visual":{"type":"image","note":""}},
 {"id":"s02","section":"wrong_answers","narration":"","visual":{"type":"prompt_card","note":""}},
 {"id":"s03","section":"real_cause","narration":"","visual":{"type":"diagram","note":""}},
 {"id":"s04","section":"fix","narration":"","visual":{"type":"prompt_card","note":""}},
 {"id":"s05","section":"verify","narration":"","visual":{"type":"split_compare","note":""}},
 {"id":"s06","section":"rule","narration":"","visual":{"type":"text_card","note":""}},
 {"id":"s07","section":"outro","narration":"이런 실패는 작업을 계속하는 한 또 나옵니다. 다음 실패도 이렇게 원인과 처방까지 정리해서 올리겠습니다. 도움이 됐다면 구독과 좋아요 부탁드립니다.","visual":{"type":"text_card","kicker":"마무리","text":"다음 실패도 이렇게 정리해서 올리겠습니다.\n도움이 됐다면 구독과 좋아요."}}
]}
EOT
echo '{}' > "$EP/script/tts_overrides.json"
echo '[["s00","실패 테이크"]]' > "$EP/script/chapters.json"
echo '{"clips":{},"stills":{},"contact":[]}' > "$EP/script/visual_prep.json"
echo "created $EP"; find "$EP" -type f | sort
