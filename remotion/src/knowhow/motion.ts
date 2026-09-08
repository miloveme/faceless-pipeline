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

export const useCue = (atSec: number, overSec = 0.5, opts?: { linear?: boolean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (opts?.linear) {
    return interpolate(frame, [atSec * fps, (atSec + overSec) * fps], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(...EASE_OUT),
    });
  }
  return spring({
    frame: frame - atSec * fps, fps,
    durationInFrames: Math.max(1, Math.round(overSec * fps)),
    config: CUE_SPRING,
  });
};
