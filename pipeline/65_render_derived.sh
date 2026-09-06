#!/bin/bash
# 썸네일 스틸(<PREFIX>-Thumb-A/B/C)과 쇼츠(<PREFIX>-Shorts-1/2) 렌더 + 정규화 → <EP>/edit
# 사용: 65_render_derived.sh <EP> [thumbs=A,B,C] [shorts=1,2]
set -e
EP=$(python3 -c "import sys;sys.path.insert(0,'$(dirname "$0")');from common import ep_dir;print(ep_dir('$1'))")
THUMBS=${2:-A,B,C}; SHORTS=${3:-1,2}
SLUG=$(basename "$EP" | cut -d_ -f1 | tr A-Z a-z); PREFIX=$(basename "$EP" | cut -d_ -f1)
REMOTION_DIR=${REMOTION_DIR:-$(cd "$(dirname "$0")/../remotion" 2>/dev/null && pwd)}; OUT=$REMOTION_DIR/out/$SLUG; mkdir -p "$OUT" "$EP/edit/thumbs"
cd "$REMOTION_DIR" && npx tsc --noEmit && echo TSC_OK
for v in ${THUMBS//,/ }; do npx remotion still "$PREFIX-Thumb-$v" "$OUT/thumb_$v.png" --log=error 2>&1 | grep -v "^$" | tail -1; cp "$OUT/thumb_$v.png" "$EP/edit/thumbs/"; done
for n in ${SHORTS//,/ }; do
  npx remotion render "$PREFIX-Shorts-$n" "$OUT/${PREFIX}_shorts_$n.mp4" --codec=h264 --crf=20 --log=error --concurrency=8 2>&1 | tail -1
  ffmpeg -v error -y -i "$OUT/${PREFIX}_shorts_$n.mp4" -vn -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 160k "$OUT/_sh$n.m4a"
  ffmpeg -v error -y -i "$OUT/${PREFIX}_shorts_$n.mp4" -i "$OUT/_sh$n.m4a" -map 0:v -map 1:a -c copy -shortest "$OUT/${PREFIX}_shorts_${n}_master.mp4"
  cp "$OUT/${PREFIX}_shorts_${n}_master.mp4" "$EP/edit/"; echo "shorts $n $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/${PREFIX}_shorts_${n}_master.mp4")s"
done
ls -la "$EP/edit/thumbs" "$EP"/edit/*_shorts_*_master.mp4
