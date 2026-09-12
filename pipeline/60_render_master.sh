#!/bin/bash
# Remotion 렌더 → loudnorm -14 리먹스(-c:v copy) → 720p 프리뷰 → 무음 검사 → <EP>/edit 복사
# 사용: 60_render_master.sh <EP> <CompositionId> <version>   예) 60_render_master.sh episodes/E01_myepisode E01-Episode v1
set -e
set -o pipefail
# **`$0` 를 나중에 쓰면 안 된다.** 이 스크립트는 아래에서 `cd "$REMOTION_DIR"` 를 하는데,
# `$0` 가 상대경로면 그때부터 `dirname "$0"` 이 딴 데를 가리킨다 —
# v10 이 다 구워 놓고 **마지막 검사에서 「파일이 없습니다」로 종료코드 2** 를 냈다.
# 여기서 한 번 절대경로로 굳힌다.
HERE=$(cd "$(dirname "$0")" && pwd)
EP=$(python3 -c "import sys;sys.path.insert(0,'$(dirname "$0")');from common import ep_dir;print(ep_dir('$1'))"); COMP=$2; VER=$3
SLUG=$(basename "$EP" | cut -d_ -f1 | tr A-Z a-z); PREFIX=$(basename "$EP" | cut -d_ -f1)
REMOTION_DIR=${REMOTION_DIR:-$(cd "$(dirname "$0")/../remotion" 2>/dev/null && pwd)}; OUT=$REMOTION_DIR/out/$SLUG; mkdir -p "$OUT" "$EP/edit"
[ -d "$REMOTION_DIR/node_modules" ] || { echo "Remotion 이 설치되지 않았습니다: $REMOTION_DIR"; echo "  cd $REMOTION_DIR && npm install"; exit 1; }
cd "$REMOTION_DIR" && npx tsc --noEmit && echo TSC_OK
RAW=$OUT/${PREFIX}_episode_${VER}.mp4; MASTER=$OUT/${PREFIX}_episode_${VER}_master.mp4; PREV=$OUT/${PREFIX}_episode_${VER}_preview720.mp4
# **묶는 순간을 적어 둔다.** Remotion 은 시작할 때 `src/` 와 `public/` 을 한 번 묶고
# 그 뒤 원본이 바뀌어도 **아무 말 없이 옛 판본을 끝까지 굽는다**. 실제로 v9 를 굽는 동안
# `parts.tsx`(02:42)·`scenes.tsx`(02:44)를 고쳤고, **02:34:52 에 시작한 마스터에는 하나도 안 들었다.**
# 그걸 모르고 그 마스터로 「고친 것이 이렇게 나왔다」를 담당 셋에게 보고했다.
BUNDLE_AT=$(date +%s)
# **동시에 여덟 장을 굽다 두 번 죽었다.** 한 장씩 뜨면 2초에 되는 프레임이,
# 여덟이 같이 돌면 30초를 넘겨 죽는다 — 크롬 탭 여덟이 저마다 `<video>` 열여덟을 들고 있어서다.
#   v10 1차  f2755(s04) — 소재보다 씬이 길어 없는 자리를 찾다 죽음 → `clip_len.json` 으로 고침
#   v10 2차  f3517(s06) — **열린 손잡이가 없는 그냥 시간 초과.** 그 프레임 한 장은 **2.0초**에 뜬다
# 그래서 **동시 수를 줄이고 기다림을 늘린다.** 느려지는 것은 값이 아니라 시간이다.
# 바꿀 일이 있으면 환경변수로 준다 — 스크립트를 고치지 않게.
CONC=${RENDER_CONCURRENCY:-4}
TMO=${RENDER_TIMEOUT_MS:-120000}
echo "렌더 설정: 동시 $CONC 장 · 한 장 기다림 ${TMO}ms  (RENDER_CONCURRENCY · RENDER_TIMEOUT_MS 로 바꿉니다)"
# 15분짜리다. tail 로 바로 삼키면 도는 동안 아무것도 안 보인다 — 전부 로그로 남기고 끝 두 줄만 띄운다.
npx remotion render "$COMP" "$RAW" --codec=h264 --crf=18 --log=error \
  --concurrency="$CONC" --timeout="$TMO" 2>&1 | tee "$OUT/_render.log" | tail -2
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
echo "--- loudness"
LOUD=$(ffmpeg -nostdin -i "$MASTER" -af ebur128=peak=true -f null - 2>&1 | grep -E " I:|Peak:" | tail -2); echo "$LOUD"
# 두 패스(linear)는 TP 한계에 걸리면 **게인을 스스로 낮춰** 목표에 못 닿는다. 그래도 멈추지 않는다 —
# 그때는 목표 도달보다 구간 관계 보존이 더 중요하다(음악 감독). 다만 조용히 -15.2 로 나가면
# 유튜브 정규화가 다시 올리면서 맞춰 놓은 관계가 흔들리므로, 벗어난 것을 한 줄 찍는다. 0.5 LU 는 음악 감독 값.
printf '%s\n' "$LOUD" | sed -n 's/.*I:[[:space:]]*\(-\{0,1\}[0-9.]*\) LUFS.*/\1/p' | tail -1 \
  | awk '{ d = $1 + 14; if (d < 0) d = -d;
           if (d > 0.5) printf "  ← 목표 -14 에서 %.1f LU 벗어났습니다. linear 가 TP 한계에 걸려 게인을 낮춘 것입니다 — 음악 감독에게 알리세요\n", d }' 
echo "--- duration $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MASTER")s"
# 무음이 하나도 없으면 grep 이 1 을 돌려준다 — 그건 정상이므로 || true
echo "--- silences >2.5s"; ffmpeg -i "$MASTER" -af "silencedetect=noise=-45dB:d=2.5" -f null - 2>&1 | grep -o "silence_start: [0-9.]*\|silence_duration: [0-9.]*" | paste - - | head || true
# **「무음이 있다」로는 아무것도 못 가린다.** 씬 사이에는 무음이 있어야 한다 —
# 앞 씬의 말이 끝나고 남은 자리 + 다음 씬의 `LEAD`. **얼마나 있어야 하는지를 시각표에서 셈해서 댄다.**
# v10 에서 s07 의 마지막 1.84초가 통째로 빠졌는데 `silencedetect` 로는 안 보였다 —
# 다른 자리와 같은 「무음」이고 **길이만 1.9초 길었다**(33곳이 1.30~1.41, 한 곳이 3.22).
echo "--- 무음이 시각표와 맞는가"
python3 "$HERE/_silence_check.py" "$MASTER" "$1" || exit 3
# **있는 검사를 여기서 부른다.** 검사가 있어도 부르는 데가 없으면 문서와 같다 —
# `check_imports.py` 는 오늘 실제로 그랬다. 있었는데 스테이지만 봐서 안 울렸다.
# 에피소드는 절대경로(`$EP`)로 넘긴다. 위에서 `cd "$REMOTION_DIR"` 을 했으므로
# `$1` 이 상대경로면 여기서부터 딴 데를 가리킨다.
# **종료코드를 그대로 넘긴다.** `|| exit 3` 으로 뭉개면 「설정 오류(2)」와 「검사 실패(3)」가
# 같은 수가 되어, 근거 파일이 없는 것과 화면이 틀린 것을 부르는 쪽이 못 가른다.
echo "--- 계획서의 카드를 이 문법이 담는가"
python3 "$HERE/46_grammar_check.py" "$EP" || exit $?
echo "--- 내레이션이 가리키는 자리에 그것이 있는가"
python3 "$HERE/47_points_check.py" "$EP" --master "$MASTER" || exit $?
# **62 는 가르지 않는다.** 정지 비율의 합격선은 미술·연출 값이고 아직 아무도 정한 적이 없다 —
# 그 파일 독스트링이 「가르는 잣대가 아니라 자리를 찾는 잣대」라고 못박아 두었다.
# 엔지니어가 여기서 수를 정하면 검사 기준을 만든 사람이 혼자 정하는 것이 된다.
# 여기서 하는 일은 **매 렌더마다 그 수가 찍히게** 하는 것까지다. 죽는 것은 검사가 못 돌 때뿐이다.
echo "--- 얼마나 정지해 있나 (판정 아님 — 미술·연출이 읽는 수다)"
python3 "$HERE/62_still_check.py" "$MASTER" --ep "$EP" || exit $?
cp "$MASTER" "$PREV" "$EP/edit/" && echo "COPIED → $EP/edit/"
# **묶은 뒤에 바뀐 원본이 있나.** 있으면 이 마스터는 지금 코드와 다르다 — 종료코드 3.
# 「없다」도 **몇 개를 봤는지** 같이 찍는다. 검사가 깨져 0 이 나온 것과 구별되지 않으면 안 된다.
STALE=$(python3 "$HERE/_render_stale.py" "$REMOTION_DIR" "$BUNDLE_AT")
SEEN=$(printf '%s\n' "$STALE" | head -1); LATE=$(printf '%s\n' "$STALE" | tail -n +2 | sed '/^$/d')
if [ -n "$LATE" ]; then
  N=$(printf '%s\n' "$LATE" | wc -l | tr -d ' ')
  echo "--- 원본 검사: **이 마스터는 지금 코드와 다릅니다** — 묶은 뒤에 $N 개가 바뀌었습니다 (본 파일 $SEEN 개)"
  printf '%s\n' "$LATE" | sed 's/^/      /'
  echo "      묶은 시각 $(date -r "$BUNDLE_AT" '+%H:%M:%S') · 이 파일들의 고침은 이 마스터에 **안 들었습니다**"
  echo "      이 마스터로 「고친 것이 이렇게 나왔다」를 보고하지 마세요. 다시 돌리세요."
  exit 3
fi
echo "--- 원본 검사: 묶은 뒤에 바뀐 것 **0개** (src·public 파일 $SEEN 개를 봤습니다)"
