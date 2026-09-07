import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE_OUT } from "./theme";

/**
 * 부품이 씬 길이를 보고 스스로 속도를 정한다.
 *
 * 왜 필요한가 — 등장 시각을 상수로 박으면 씬 길이와 무관하게 늘 같은 시각에 끝난다.
 * E00 첫 조립에서 표는 2.2초에 다 떠 버리는데 같은 내용을 읽는 내레이션은 19초였다.
 * 전편 402초 중 281초가 정지 화면이었다.
 *
 * 씬은 Episode.tsx 가 Sequence 안에서 그리므로 useVideoConfig().durationInFrames 가
 * **그 씬의 길이**다. 그래서 부품은 씬마다 값을 받지 않아도 자기 속도를 계산할 수 있다.
 *
 * 지키는 것 셋:
 *   1. 연출이 everySec 을 주면 그것이 이긴다 (이미 손으로 맞춘 씬이 있다)
 *   2. 마지막 요소가 씬이 끝나는 순간 뜨면 못 읽는다 → 뒤에 HOLD 만큼 남긴다
 *   3. 너무 느리면 내레이션이 이미 말한 것이 화면에 없다 → 전체 폭에 상한을 둔다
 */

/* ─────────── 시각표가 만드는 여백 ───────────
 * 씬 = 0.5초 + 내레이션 + 0.8초 (_pipeline/common.py 의 LEAD/PAD).
 * scenes_v2.json 24개 씬 전부 이 구조다 — 실측으로 확인했다. */
export const SCENE_LEAD = 0.5;
export const SCENE_TAIL = 0.8;

/* ─────────── 이 편에서 잰 내레이션 속도 ───────────
 * src/e00/data/captions.json, 문장 121개
 *   문장 하나       중앙값 2.88초 (평균 3.03)
 *   씬의 마지막 문장 중앙값 2.39초 (평균 2.51)
 *   나열할 때 항목 하나 1.19~1.36초
 *     s01 "대본은 A, 음성은 B, 검사는 C"  3항목 / 4.07초 = 1.36
 *     s02 "주제를 정하고, 대본을 쓰고, …"  6단계 / 6.26초 = 1.04
 *     s04 대본 구조 8단계 / 9.3초        = 1.16
 */
const LAST_SENTENCE = 2.4;

/** 마지막 요소가 다 뜬 뒤 남겨 두는 시간.
 *  마지막 문장(2.4초)을 듣는 동안 + 씬 꼬리(0.8초) 동안 읽을 수 있어야 한다. */
export const HOLD = LAST_SENTENCE + SCENE_TAIL; // 3.2

/** 한 요소가 켜지는 데 걸리는 시간. 기존 카드들이 쓰던 값과 같다. */
export const FADE = 0.6;

/** 첫 요소는 내레이션(0.5초)이 시작될 때 이미 떠 있어야 한다. */
const FIRST = 0.3;

/** 간격 상한의 근거 — 씬마다 내레이션이 요소를 처음 소개하는 시각을 자막에서 재 봤다.
 *  첫 요소부터 마지막 요소까지 걸린 시간:
 *    s01 7.6  s02 6.3  s04 9.3  s05 6.9  s07 10.0  s11 15.0
 *    s13 10.3 s14 11.6 s15 5.1  s16 6.1  s21 11.5   → 중앙값 9.3, 평균 9.1
 *  요소가 여섯이든 셋이든 이 값이 비슷하다. 내레이션은 나열을 한 덩어리로 하고
 *  나머지 시간은 설명에 쓰기 때문이다. 그래서 상한은 간격이 아니라 **전체 폭**에 건다.
 *  9초를 넘겨 늘리면 늦게 뜨는 요소가 생긴다 — 10.5초로 해 보면 s01 넷째 줄이
 *  내레이션보다 2.1초 늦는다. 9.0 에서는 가장 늦은 것이 s02 여섯째 0.6초다. */
const SPREAD = 9.0;

/* ─────────── SPREAD 는 폭이지 자리가 아니다 ───────────
 * 연출이 실측해 온 것: span 이 SPREAD 보다 넓은 씬에서는
 *   end = from + SPREAD + fade
 * 가 되어 **요소 개수와 무관한 상수**가 된다. 기본값이면 0.3 + 9.0 + 0.6 = 9.9초.
 * 24개 씬 중 10개(s02 s04 s05 s07 s08 s13 s14 s15 s16 s21)의 마지막 등장이
 * 여기에 못 박혀 있었고, 그 뒤 정지가 합계 78.6초였다.
 *
 * 내가 "요소를 더 쪼개면 채워진다"고 한 진단은 틀렸다. 쪼개도 end 는 안 움직인다.
 *
 * 그렇다고 SPREAD 를 올리는 것은 고침이 아니다 — 이 값은 **폭**이고, 모자란 것은 **자리**다.
 *   · 나열이 8~16초에 오는 씬에서 SPREAD 를 16 으로 올리면 첫 요소는 여전히 0.3 에 뜬다.
 *     정지는 뒤에서 앞으로 옮겨질 뿐이고, 대신 요소가 내레이션보다 먼저 떠 버린다.
 *   · SPREAD 를 넓히면 늦게 뜨는 요소가 생긴다(10.5 로 재 봤을 때 s01 넷째 줄 2.1초 지각).
 *     지루한 것보다 틀린 것이 나쁘다.
 * 그래서 고칠 자리는 SPREAD 가 아니라 o.from / o.until 이다. 둘 다 이미 여기 있었는데
 * 부품이 밖으로 안 내놓아서 연출이 쓸 수 없었다. 부품에 fromSec / untilSec 을 열었다. */

/** 하한. 이보다 빠르면 차례로 켜지는 것으로 안 읽히고 한꺼번에 뜬 것처럼 보인다. */
const FLOOR = 0.35;

export type PaceOpts = {
  /** 연출이 준 간격. 있으면 계산을 건너뛴다. */
  everySec?: number;
  /** 한 요소가 켜지는 데 걸리는 시간 */
  fade?: number;
  /** 첫 요소가 켜지기 시작하는 시각 */
  from?: number;
  /** 마지막 요소가 **다 켜져 있어야** 하는 시각. 기본은 씬끝 − HOLD */
  until?: number;
};

export type Pace = {
  gap: number;
  fade: number;
  from: number;
  /** i번째 요소가 켜지는 [시작, 끝] 초 */
  at: (i: number) => [number, number];
  /** 마지막 요소가 다 켜지는 시각 */
  end: number;
  /** 씬 길이(초) */
  dur: number;
};

/** 같은 잘못을 한 번만 말한다. 렌더는 프레임마다 도므로 그냥 찍으면 수천 줄이 된다. */
const said = new Set<string>();
/**
 * console.warn 이 아니라 console.error 로 찍는다. 던지는 것이 아니다 — 채널만 다르다.
 *
 * 이유는 렌더 기계에 있다. remotion 의 CLI 는 부품이 찍은 로그를 이렇게 나른다:
 *   console.error → `--log=error` 에서도 나온다
 *   console.warn  → `--log=verbose` 에서만 나온다
 * (`npx remotion still` 은 아예 안 나른다. 마스터를 뽑는 건 render 다.)
 * 마스터 렌더는 `--log=error` 로 돌므로, warn 으로 두면 NODE_ENV 가드를 뗀 것이
 * 헛일이 된다 — 정확히 마스터를 뽑을 때만 입을 다무는 문지기가 그대로 남는다.
 * 실측: 60프레임 시험 렌더에서 warn 은 `--log=error` 로그에 0줄, error 는 나왔다.
 */
const warnOnce = (key: string, msg: string) => {
  if (said.has(key)) return;
  said.add(key);
  console.error(msg);
};

/** 순수 계산. 렌더 없이 시험할 수 있게 훅 밖으로 빼 뒀다. */
export const paceIn = (dur: number, count: number, o: PaceOpts = {}): Pace => {
  const from = o.from ?? FIRST;
  const fade = o.fade ?? FADE;
  // 마지막 요소가 **켜지기 시작**할 수 있는 마지막 시각
  const last = (o.until ?? dur - HOLD) - fade;
  const span = Math.max(0, last - from);
  const n = Math.max(1, count);
  // 창이 좁으면 창에 맞추고, 넓으면 SPREAD 만큼만 쓴다. 남는 시간은 읽는 시간이 된다.
  const spread = Math.min(span, SPREAD);
  const auto = n <= 1 ? 0 : Math.max(FLOOR, spread / (n - 1));
  const gap = o.everySec ?? auto;
  const end = from + (n - 1) * gap + fade;
  // fromSec 을 손으로 넣다 보면 마지막 요소가 씬 밖으로 나가는 일이 생긴다.
  // 산문 규칙은 재발하므로 기계가 말하게 둔다. 설정당 한 번만.
  //
  // 던지지 않고 말만 한다 — 이건 리듬 결정의 결과지 오타가 아니다.
  // "항목을 줄일 것인가 · 일찍 시작할 것인가 · 그냥 둘 것인가"는 연출이 정한다.
  // 던질지 말지도 연출이 정할 때까지 지금 동작을 유지한다.
  //
  // 다만 NODE_ENV 가드는 뗐다. 렌더 번들은 production 이라 그 가드는
  // **정확히 마스터를 뽑을 때만 입을 다무는 문지기**였다. 말은 하게 둔다.
  if (end > dur) {
    warnOnce(
      `${dur}|${count}|${from}|${gap}|${fade}`,
      `[pacing] 마지막 요소가 씬 밖에서 끝난다 — 씬 ${dur.toFixed(2)}초, 요소 ${count}개, ` +
        `from ${from}, gap ${gap.toFixed(2)}, end ${end.toFixed(2)}. fromSec 을 당기거나 요소를 줄인다.`,
    );
  }
  return {
    gap,
    fade,
    from,
    dur,
    at: (i: number) => [from + i * gap, from + i * gap + fade],
    end,
  };
};

/* ─────────── 각주·꼬리말은 본문과 다른 시계를 쓴다 ───────────
 * 지금까지 TableCard 의 note, ListCard 의 footer, TimeBars 의 note 를
 * 본문 나열의 마지막 요소로 세어 usePace 에 함께 넣었다. 이것이 잘못이었다.
 *   · 각주는 나열의 한 항목이 아니다. 내레이션에서 나열이 끝나고 한참 뒤에 온다.
 *   · 함께 세면 같은 SPREAD 를 한 칸 더 나눠 본문이 빨라지고, 각주는 end(9.9초)에 못 박힌다.
 *   · s01 각주는 자막 9.36("무료")과 14.34("클라우드 과금") 두 곳을 혼자 감당한다.
 *     한 줄로는 어느 쪽에도 못 맞는다.
 * 그래서 꼬리 줄은 (1) 여러 줄이 될 수 있고 (2) 줄마다 절대 시각을 받는다.
 *
 * 규칙 하나: **시각이 붙은 줄은 본문 나열의 슬롯을 쓰지 않는다.**
 * 안 그러면 손으로 시각을 준 각주가 본문 간격까지 좁힌다. */
export type Tail = {
  lines: string[];
  /** 시각이 안 붙어 자동 나열에 얹혀야 하는 줄 수. usePace 의 count 에 더한다. */
  extra: number;
  /** i번째 꼬리 줄의 [시작, 끝] 초. slotBase = 본문 요소 수 */
  at: (i: number, p: Pace, slotBase: number) => [number, number];
};

export const tailLines = (text?: string | string[], at?: number | number[]): Tail => {
  const lines = text == null ? [] : Array.isArray(text) ? text : [text];
  const ats = at == null ? [] : Array.isArray(at) ? at : [at];
  const times = lines.map((_, i) => ats[i]);
  return {
    lines,
    extra: times.filter((t) => t == null).length,
    at: (i, p, slotBase) => {
      const fixed = times[i];
      if (fixed != null) return [fixed, fixed + p.fade];
      // 앞쪽 줄 중 시각이 안 붙은 것만 세어 자동 슬롯을 차례로 준다.
      const auto = times.slice(0, i).filter((t) => t == null).length;
      return p.at(slotBase + auto);
    },
  };
};

/** 이 씬이 몇 초짜리인가. Sequence 안에서만 뜻이 있다. */
export const useSceneSec = () => {
  const { fps, durationInFrames } = useVideoConfig();
  return durationInFrames / fps;
};

/** 씬 길이를 스스로 읽어서 속도를 정한다. Sequence 안에서만 뜻이 있다. */
export const usePace = (count: number, o: PaceOpts = {}): Pace => {
  const { fps, durationInFrames } = useVideoConfig();
  return paceIn(durationInFrames / fps, count, o);
};

/** [from, to] 초 사이에 0→1. 카드들이 쓰던 e() 와 같은 것. */
export const useEaseIn = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (from: number, to: number) =>
    interpolate(frame, [from * fps, to * fps], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(...EASE_OUT),
    });
};

/** 로그처럼 줄이 흐르는 것. 요소 하나씩 켜지는 것과 달리 페이드가 없다.
 *  간격 상한이 다르다 — 로그는 나열이 아니라 흐름이라 2초에 한 줄이면 멈춘 것처럼 보인다. */
export const useStreamPace = (lines: number, everySec?: number, startSec = 0.7) => {
  const { fps, durationInFrames } = useVideoConfig();
  const dur = durationInFrames / fps;
  const span = Math.max(0, dur - HOLD - startSec);
  const auto = lines < 1 ? 0 : Math.min(2.4, Math.max(0.12, span / lines));
  return { startSec, everySec: everySec ?? auto };
};
