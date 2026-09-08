import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE_OUT } from "./theme";

/**
 * 씬 시작 기준 초 → 0~1. **씬 안 움직임은 전부 이 값에서 나온다.**
 *
 * 이 값을 `opacity` 에만 물리면 화면이 나타나고 멈춘다. E01 v2 마스터를 재 보니
 * **자막을 뺀 화면이 평균 80% 시간 정지**였고 `s03` 은 16.5초 중 94%였다.
 * **같은 값을 크기·위치·색·숫자·막대 길이에 물리면 그게 모션 그래픽이다** — 부품을 새로 만들 것이 없다.
 *
 * 기본이 `spring` 이다. 선형으로 움직이면 값이 변해도 **기계처럼 보인다**.
 * 다만 **속도가 뜻인 자리**(타이핑 · 카라오케 · 초당 몇 줄)는 `linear: true` 로 선형을 쓴다 —
 * 거기서 튀면 「초당 N자」가 거짓이 된다.
 */
export const CUE_SPRING = { damping: 200, mass: 1, stiffness: 100 };
//  ^ 느낌 값이다(미술·연출 영역). damping 200 은 넘침이 없는 감쇠 —
//    글자·상자가 목표를 지나쳤다 돌아오면 읽는 눈이 따라가느라 피로하다.
//    튕김이 필요한 자리가 생기면 그 씬에서 config 를 따로 준다.

/**
 * 훅이 아닌 알맹이. **`map` 안에서 박자를 여럿 쓸 때 쓴다** — 반복문 안에서 훅을 부르면
 * 개수가 데이터에 따라 바뀌는 순간 훅 순서가 어긋난다. 프레임은 `useCues()` 로 한 번만 읽는다.
 */
export const cue = (frame: number, fps: number, atSec: number, overSec = 0.5, linear = false) => {
  if (linear) {
    return interpolate(frame, [atSec * fps, (atSec + overSec) * fps], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(...EASE_OUT),
    });
  }
  const dur = Math.max(1, Math.round(overSec * fps));
  const f = frame - atSec * fps;
  if (f >= dur) return 1;
  return spring({ frame: f, fps, durationInFrames: dur, config: CUE_SPRING });
};

/** 한 씬에서 박자를 여럿 쓰는 자리. 훅은 한 번만 부르고 함수를 받는다. */
export const useCues = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (atSec: number, overSec = 0.5, linear = false) => cue(frame, fps, atSec, overSec, linear);
};

export const useCue = (atSec: number, overSec = 0.5, opts?: { linear?: boolean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (opts?.linear) {
    return interpolate(frame, [atSec * fps, (atSec + overSec) * fps], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(...EASE_OUT),
    });
  }
  const dur = Math.max(1, Math.round(overSec * fps));
  const f = frame - atSec * fps;
  // 끝에서 **정확히 1** 로 만든다. spring 은 durationInFrames 끝에서 0.9959 를 준다 —
  // opacity 는 무해하지만 「막대가 끝까지 자란다」 같은 자리에서는 끝이 모자란다.
  // 실제로 s08 밑줄이 5px 짧아졌다(다른 화소 34개, 7×6 자리). 눈에 안 걸리고 렌더도 안 죽는다.
  if (f >= dur) return 1;
  return spring({ frame: f, fps, durationInFrames: dur, config: CUE_SPRING });
};
