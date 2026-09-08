#!/bin/bash
# 썸네일 스틸(<PREFIX>-Thumb-A/B/C, 축소본 포함)과 쇼츠(<PREFIX>-Shorts-1/2) 렌더 + 정규화 → <EP>/edit
# 사용: 65_render_derived.sh <EP> [thumbs=A,B,C] [shorts=1,2] [widths=168,300,480]
set -e
set -o pipefail
EP=$(python3 -c "import sys;sys.path.insert(0,'$(dirname "$0")');from common import ep_dir;print(ep_dir('$1'))")
# **빈 값은 「없음」이다.** `${2:-…}` 로 쓰면 `""` 를 줘도 기본값이 들어와 안 부른 것이 돌아간다 —
# 썸네일만 뽑으려고 shorts 에 "" 를 줬더니 쇼츠 둘이 같이 구워졌다. `${2-…}` 는 **안 준 것만** 채운다.
THUMBS=${2-A,B,C}; SHORTS=${3-1,2}
# **표시 폭은 잰 값이 아니라 가정이다**(미술). 그래서 하나로 안 두고 셋으로 두고,
# **결론이 셋 다에서 같은 것만 값으로 쓴다.** 실제 폭은 승인 3(업로드) 때 화면에서 본다.
# 축소는 **Lanczos** 다 — 목록 화면 캡처는 브라우저·기기마다 달라 재현이 안 된다(미술).
WIDTHS=${4:-168,300,480}
SLUG=$(basename "$EP" | cut -d_ -f1 | tr A-Z a-z); PREFIX=$(basename "$EP" | cut -d_ -f1)
REMOTION_DIR=${REMOTION_DIR:-$(cd "$(dirname "$0")/../remotion" 2>/dev/null && pwd)}; OUT=$REMOTION_DIR/out/$SLUG; mkdir -p "$OUT" "$EP/edit/thumbs"
[ -d "$REMOTION_DIR/node_modules" ] || { echo "Remotion 이 설치되지 않았습니다: $REMOTION_DIR"; echo "  cd $REMOTION_DIR && npm install"; exit 1; }
cd "$REMOTION_DIR" && npx tsc --noEmit && echo TSC_OK
for v in ${THUMBS//,/ }; do
  # --log=error 면 출력이 아예 없을 수 있어 grep 이 1 을 돌려준다. 성패는 파일로 판정한다.
  npx remotion still "$PREFIX-Thumb-$v" "$OUT/thumb_$v.png" --log=error 2>&1 | grep -v "^$" | tail -1 || true
  [ -s "$OUT/thumb_$v.png" ] || { echo "스틸 렌더 실패: $PREFIX-Thumb-$v"; echo "  목록: cd $REMOTION_DIR && npx remotion compositions"; exit 1; }
  # 실제로 보이는 크기로도 같이 뽑는다. 1280 으로 크게 보면 안 보이고 줄이면 바로 보이는
  # 결함이 있다 — 글자에 가려 한쪽 얼굴만 안 읽히는 것을 E01 에서 세 번 돌고 나서야 잡았다.
  # **썸네일은 h264 를 안 거친다** — PNG 로 나가므로 획 3px 하한·키프레임 같은 영상 잣대는
  # 여기서 뜻이 없다. **작아지는 것만이 잣대다.**
  cp "$OUT/thumb_$v.png" "$EP/edit/thumbs/"
  for w in ${WIDTHS//,/ }; do
    ffmpeg -nostdin -v error -y -i "$OUT/thumb_$v.png" -vf "scale=$w:-2:flags=lanczos" "$OUT/thumb_${v}_$w.png"
    cp "$OUT/thumb_${v}_$w.png" "$EP/edit/thumbs/"
  done
done
for n in ${SHORTS//,/ }; do
  npx remotion render "$PREFIX-Shorts-$n" "$OUT/${PREFIX}_shorts_$n.mp4" --codec=h264 --crf=20 --log=error --concurrency=8 2>&1 | tail -1
  [ -s "$OUT/${PREFIX}_shorts_$n.mp4" ] || { echo "쇼츠 렌더 결과가 없습니다: $PREFIX-Shorts-$n"; exit 1; }
  ffmpeg -v error -y -i "$OUT/${PREFIX}_shorts_$n.mp4" -vn -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 160k "$OUT/_sh$n.m4a"
  ffmpeg -v error -y -i "$OUT/${PREFIX}_shorts_$n.mp4" -i "$OUT/_sh$n.m4a" -map 0:v -map 1:a -c copy -shortest "$OUT/${PREFIX}_shorts_${n}_master.mp4"
  cp "$OUT/${PREFIX}_shorts_${n}_master.mp4" "$EP/edit/"; echo "shorts $n $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/${PREFIX}_shorts_${n}_master.mp4")s"
done
ls -la "$EP/edit/thumbs" "$EP"/edit/*_shorts_*_master.mp4
