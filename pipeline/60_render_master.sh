#!/bin/bash
# Remotion 렌더 → loudnorm -14 리먹스(-c:v copy) → 720p 프리뷰 → 무음 검사 → <EP>/edit 복사
# 사용: 60_render_master.sh <EP> <CompositionId> <version>   예) 60_render_master.sh episodes/E01_myepisode E01-Episode v1
set -e
set -o pipefail
EP=$(python3 -c "import sys;sys.path.insert(0,'$(dirname "$0")');from common import ep_dir;print(ep_dir('$1'))"); COMP=$2; VER=$3
SLUG=$(basename "$EP" | cut -d_ -f1 | tr A-Z a-z); PREFIX=$(basename "$EP" | cut -d_ -f1)
REMOTION_DIR=${REMOTION_DIR:-$(cd "$(dirname "$0")/../remotion" 2>/dev/null && pwd)}; OUT=$REMOTION_DIR/out/$SLUG; mkdir -p "$OUT" "$EP/edit"
[ -d "$REMOTION_DIR/node_modules" ] || { echo "Remotion 이 설치되지 않았습니다: $REMOTION_DIR"; echo "  cd $REMOTION_DIR && npm install"; exit 1; }
cd "$REMOTION_DIR" && npx tsc --noEmit && echo TSC_OK
RAW=$OUT/${PREFIX}_episode_${VER}.mp4; MASTER=$OUT/${PREFIX}_episode_${VER}_master.mp4; PREV=$OUT/${PREFIX}_episode_${VER}_preview720.mp4
# 15분짜리다. tail 로 바로 삼키면 도는 동안 아무것도 안 보인다 — 전부 로그로 남기고 끝 두 줄만 띄운다.
npx remotion render "$COMP" "$RAW" --codec=h264 --crf=18 --log=error --concurrency=8 2>&1 | tee "$OUT/_render.log" | tail -2
echo "렌더 로그: $OUT/_render.log"
[ -s "$RAW" ] || { echo "렌더 결과가 없습니다: $RAW"; echo "  컴포지션 이름이 맞는지 확인하세요 (지금 값: $COMP)"; echo "  목록: cd $REMOTION_DIR && npx remotion compositions"; exit 1; }
# loudnorm 을 **두 패스로** 건다. 한 패스는 dynamic 이라 구간마다 다른 양을 올린다 —
# 실측: 인트로 클론 +3.9 · 꼬리 +2.8 로 갈려서 의도한 2.6 LU 차이가 3.7 로 벌어졌다.
# 두 패스(linear)는 전 구간을 같은 +2.8 로 올려 관계를 그대로 둔다. 소리 판단이 화면 밖에서
# 뒤집히면 안 되는 자리다(음악 감독이 인트로 원본·클론을 0.3 LU 로 맞춰 놓은 것이 그렇다).
LN="loudnorm=I=-14:TP=-1.5:LRA=11"
MEAS=$(ffmpeg -nostdin -hide_banner -i "$RAW" -af "$LN:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
LN2=$(python3 -c "
import json,sys
try: m = json.loads(sys.argv[1])
except Exception as e: sys.exit('loudnorm 측정값을 못 읽었습니다: %s' % e)
need = ('input_i','input_tp','input_lra','input_thresh','target_offset')
miss = [k for k in need if k not in m]
if miss: sys.exit('loudnorm 측정값에 %s 가 없습니다' % ', '.join(miss))
print('$LN:measured_I=%(input_i)s:measured_TP=%(input_tp)s:measured_LRA=%(input_lra)s'
      ':measured_thresh=%(input_thresh)s:offset=%(target_offset)s:linear=true' % m)" "$MEAS") \
  || { echo "1패스 측정에 실패했습니다 — 조용히 한 패스로 넘어가지 않습니다(구간 관계가 바뀝니다)"; exit 1; }
ffmpeg -v error -y -i "$RAW" -vn -af "$LN2" -ar 48000 -c:a aac -b:a 192k "$OUT/_audio_norm.m4a"
ffmpeg -v error -y -i "$RAW" -i "$OUT/_audio_norm.m4a" -map 0:v -map 1:a -c copy -shortest "$MASTER"
ffmpeg -v error -y -i "$MASTER" -vf scale=1280:-2 -c:v libx264 -crf 24 -preset fast -c:a aac -b:a 128k "$PREV"
echo "--- loudness"; ffmpeg -i "$MASTER" -af ebur128=peak=true -f null - 2>&1 | grep -E " I:|Peak:" | tail -2
echo "--- duration $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MASTER")s"
# 무음이 하나도 없으면 grep 이 1 을 돌려준다 — 그건 정상이므로 || true
echo "--- silences >2.5s"; ffmpeg -i "$MASTER" -af "silencedetect=noise=-45dB:d=2.5" -f null - 2>&1 | grep -o "silence_start: [0-9.]*\|silence_duration: [0-9.]*" | paste - - | head || true
cp "$MASTER" "$PREV" "$EP/edit/" && echo "COPIED → $EP/edit/"
