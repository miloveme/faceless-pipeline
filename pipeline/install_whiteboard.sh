#!/bin/bash
# 손그림 애니메이션 도구 설치 (선택).
# 개념 설명 구간에서만 쓰는 도구라 필요할 때 설치하면 됩니다. → docs/VISUALS.md
set -e
set -o pipefail
DEST="${WHITEBOARD_DIR:-$HOME/.claude/skills/srt-whiteboard-animation}"
REPO="https://github.com/miloveme/srt-whiteboard-animation.git"

if [ -d "$DEST/.git" ]; then
  echo "이미 있습니다: $DEST"
  echo "최신으로 받으려면: git -C \"$DEST\" pull"
else
  mkdir -p "$(dirname "$DEST")"
  echo "받는 중: $REPO"
  git clone --depth 1 "$REPO" "$DEST"
fi

echo
echo "파이썬 환경 준비 (저장소 자체 .venv 사용)"
python3 "$DEST/scripts/prepare_env.py" || {
  echo "환경 준비에 실패했습니다. 직접 실행해 보세요:"
  echo "  python3 \"$DEST/scripts/prepare_env.py\""
  exit 1
}

echo
echo "설치 완료: $DEST"
echo "Claude Code 에서 스킬로 잡히려면 ~/.claude/skills/ 아래에 있어야 합니다 (기본 경로가 그렇습니다)."
echo "쓰는 법: pipeline/80_whiteboard_srt.py 로 구간 SRT 를 뽑은 뒤 그 SRT 로 실행하세요."
echo "렌더할 때 자막은 반드시 끄세요 — Remotion 이 이미 자막을 굽습니다."
