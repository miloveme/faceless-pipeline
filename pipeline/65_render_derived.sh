#!/bin/bash
# 썸네일 스틸(<PREFIX>-Thumb-A/B/C, 360px 축소본 포함)과 쇼츠(<PREFIX>-Shorts-1/2) 렌더 + 정규화 → <EP>/edit
# 사용: 65_render_derived.sh <EP> [thumbs=A,B,C] [shorts=1,2]
set -e
set -o pipefail
EP=$(python3 -c "import sys;sys.path.insert(0,'$(dirname "$0")');from common import ep_dir;print(ep_dir('$1'))")
THUMBS=${2:-A,B,C}; SHORTS=${3:-1,2}
SLUG=$(basename "$EP" | cut -d_ -f1 | tr A-Z a-z); PREFIX=$(basename "$EP" | cut -d_ -f1)
REMOTION_DIR=${REMOTION_DIR:-$(cd "$(dirname "$0")/../remotion" 2>/dev/null && pwd)}; OUT=$REMOTION_DIR/out/$SLUG; mkdir -p "$OUT" "$EP/edit/thumbs"
[ -d "$REMOTION_DIR/node_modules" ] || { echo "Remotion 이 설치되지 않았습니다: $REMOTION_DIR"; echo "  cd $REMOTION_DIR && npm install"; exit 1; }
cd "$REMOTION_DIR" && npx tsc --noEmit && echo TSC_OK
for v in ${THUMBS//,/ }; do
  # --log=error 면 출력이 아예 없을 수 있어 grep 이 1 을 돌려준다. 성패는 파일로 판정한다.
  npx remotion still "$PREFIX-Thumb-$v" "$OUT/thumb_$v.png" --log=error 2>&1 | grep -v "^$" | tail -1 || true
  [ -s "$OUT/thumb_$v.png" ] || { echo "스틸 렌더 실패: $PREFIX-Thumb-$v"; echo "  목록: cd $REMOTION_DIR && npx remotion compositions"; exit 1; }
  # 실제로 보이는 크기로도 같이 뽑는다. 1280 으로 크게 보면 안 보이고 360 으로 줄이면 바로 보이는
  # 결함이 있다 — 글자에 가려 한쪽 얼굴만 안 읽히는 것을 E01 에서 세 번 돌고 나서야 잡았다.
  ffmpeg -nostdin -v error -y -i "$OUT/thumb_$v.png" -vf scale=360:-2 "$OUT/thumb_${v}_360.png"
  cp "$OUT/thumb_$v.png" "$OUT/thumb_${v}_360.png" "$EP/edit/thumbs/"
done
for n in ${SHORTS//,/ }; do
  npx remotion render "$PREFIX-Shorts-$n" "$OUT/${PREFIX}_shorts_$n.mp4" --codec=h264 --crf=20 --log=error --concurrency=8 2>&1 | tail -1
  [ -s "$OUT/${PREFIX}_shorts_$n.mp4" ] || { echo "쇼츠 렌더 결과가 없습니다: $PREFIX-Shorts-$n"; exit 1; }
  ffmpeg -v error -y -i "$OUT/${PREFIX}_shorts_$n.mp4" -vn -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 160k "$OUT/_sh$n.m4a"
  ffmpeg -v error -y -i "$OUT/${PREFIX}_shorts_$n.mp4" -i "$OUT/_sh$n.m4a" -map 0:v -map 1:a -c copy -shortest "$OUT/${PREFIX}_shorts_${n}_master.mp4"
  cp "$OUT/${PREFIX}_shorts_${n}_master.mp4" "$EP/edit/"; echo "shorts $n $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/${PREFIX}_shorts_${n}_master.mp4")s"
done
ls -la "$EP/edit/thumbs" "$EP"/edit/*_shorts_*_master.mp4
