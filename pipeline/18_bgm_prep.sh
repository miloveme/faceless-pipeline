#!/bin/bash
# BGM 원본 → -27 LUFS, 페이드 인 2s/아웃 3s → Remotion public/<slug>/bgm_lofi.mp3 + <EP>/audio/
# 사용: 18_bgm_prep.sh <EP> <bgm_raw.mp3>
set -e
EP=$(python3 -c "import sys;sys.path.insert(0,'$(dirname "$0")');from common import ep_dir;print(ep_dir('$1'))"); SRC=$2
SLUG=$(basename "$EP" | cut -d_ -f1 | tr A-Z a-z); REMOTION_DIR=${REMOTION_DIR:-$(cd "$(dirname "$0")/../remotion" 2>/dev/null && pwd)}; PUB=$REMOTION_DIR/public/$SLUG; mkdir -p "$PUB"
ffmpeg -v error -y -i "$SRC" -af "loudnorm=I=-27:TP=-6:LRA=9,afade=t=in:d=2,areverse,afade=t=in:d=3,areverse" -ar 44100 -b:a 160k "$PUB/bgm_lofi.mp3"
cp "$PUB/bgm_lofi.mp3" "$EP/audio/bgm_lofi.mp3"
ffmpeg -i "$PUB/bgm_lofi.mp3" -af ebur128 -f null - 2>&1 | grep " I:" | tail -1
