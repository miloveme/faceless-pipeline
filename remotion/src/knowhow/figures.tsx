import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { T, faceFor } from "./theme";
import { useCue } from "./motion";

/**
 * 시간축이 뜻인 화면의 부품들.
 *
 * **막대 길이·숫자가 값 그 자체이면 `linear` 다.** px/초가 실제 초와 비례해야 하고,
 * 1.6초 막대는 1.6초 동안 자라야 한다. `spring` 은 **자리를 잡는 것**(조각이 내려앉음,
 * 점이 찍힘)에만 쓴다 — 가·감속이 붙으면 **자라는 도중의 길이가 거짓**이 된다.
 * 두 막대를 나란히 놓고 「어느 쪽이 짧은가」를 보는 자리에서 특히 그렇다.
 */

/** 자리를 잡는 움직임. 오버슈트 0 — 지나쳤다 돌아오면 「지나쳤다」가 된다(미술). */
export const SETTLE = { stiffness: 100, mass: 1, damping: 26 };
export const useSettle = (atSec: number, overSec = 0.5) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.max(1, Math.round(overSec * fps));
  const f = frame - atSec * fps;
  if (f >= dur) return 1;
  return spring({ frame: f, fps, durationInFrames: dur, config: SETTLE });
};

/** 0 → 1 을 **선형으로**. 값이 곧 길이인 자리에 쓴다. */
export const useGrow = (atSec: number, overSec: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return interpolate(frame, [atSec * fps, (atSec + overSec) * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
};

/**
 * 값이 길이인 막대. `px` 는 **눈금 × 값**으로 바깥에서 계산해 넘긴다 —
 * 여기서 눈금을 정하면 여러 막대가 서로 다른 눈금을 갖게 된다.
 */
export const Bar: React.FC<{
  px: number; h: number; at: number; over: number; color?: string;
  radius?: number; style?: React.CSSProperties;
}> = ({ px, h, at, over, color = T.accent, radius = 8, style }) => {
  const p = useGrow(at, over);
  return <div style={{ width: px * p, height: h, backgroundColor: color, borderRadius: radius, ...style }} />;
};

/** 못 간 만큼(빈 테두리) 또는 잘린 만큼(어두운 꼬리)을 뒤에 남기는 막대. */
export const BarWithRest: React.FC<{
  px: number; restPx: number; h: number; at: number; over: number;
  restKind: "outline" | "tail"; radius?: number;
}> = ({ px, restPx, h, at, over, restKind, radius = 8 }) => (
  <div style={{ position: "relative", width: px + restPx, height: h }}>
    {/* **남는 것은 둘 다 막대 끝 뒤에 붙는다.** 못 간 만큼도 잘린 만큼도 `u` 에서 max(want,have) 까지다 —
        꼬리를 left:0 에 두면 막대 밑에 깔려 안 보인다(실제로 그렇게 돼 있어 「자름」 넷이 안 갈렸다). */}
    <div style={{
      position: "absolute", left: px, top: 0,
      width: restPx, height: h, borderRadius: radius,
      ...(restKind === "outline"
        ? { border: `${T.lineW}px solid ${T.panelLine}` }
        : { backgroundColor: T.panel }),
    }} />
    <div style={{ position: "absolute", left: 0, top: 0 }}>
      <Bar px={px} h={h} at={at} over={over} radius={radius} />
    </div>
  </div>
);

/** 숫자가 세어진다. **선형이다** — 세는 속도가 고르지 않으면 「세는 것」으로 안 보인다. */
export const CountUp: React.FC<{
  to: number; at: number; over: number; from?: number; digits?: number;
  suffix?: string; style?: React.CSSProperties;
}> = ({ to, at, over, from = 0, digits = 0, suffix = "", style }) => {
  const p = useGrow(at, over);
  const v = (from + (to - from) * p).toFixed(digits);
  return <span style={{ fontFamily: faceFor(v + suffix), fontVariantNumeric: "tabular-nums", ...style }}>{v}{suffix}</span>;
};

/**
 * 흩어진 조각이 한 줄로 모인다. 조각은 자기 자리에 놓여 있다가 `at` 에 이어 붙는다.
 * **자리를 잡는 것이라 `spring`** 이다.
 */
export const Merge: React.FC<{
  at: number; over?: number; gapFrom: number; children: React.ReactNode;
}> = ({ at, over = 0.6, gapFrom, children }) => {
  const p = useSettle(at, over);
  return (
    <div style={{ display: "flex", gap: gapFrom * (1 - p) }}>{children}</div>
  );
};

/**
 * 두 띠가 겹치고 잘린다(s18·s20·s23). **눈금을 공유하지 않는 두 띠**를 위한 것이 아니다 —
 * 여기서는 같은 눈금 위에서 한쪽을 밀어 겹친 뒤 겹친 구간만 밝힌다.
 * 미는 것은 `spring`(자리 잡기), 밝히는 것은 `opacity` 다.
 */
export const Overlap: React.FC<{
  w: number; h: number; shiftPx: number; at: number;
  litFrom: number; litTo: number; litAt: number; color?: string;
}> = ({ w, h, shiftPx, at, litFrom, litTo, litAt, color = T.accent }) => {
  const moved = useSettle(at, 1.0);
  const lit = useCue(litAt, 0.5);
  return (
    <div style={{ position: "relative", width: w + shiftPx, height: h }}>
      <div style={{
        position: "absolute", left: shiftPx * moved, top: 0, width: w, height: h,
        backgroundColor: T.panel, border: `${T.lineW}px solid ${T.panelLine}`, borderRadius: 8,
      }} />
      <div style={{
        position: "absolute", left: litFrom, top: 0, width: litTo - litFrom, height: h,
        backgroundColor: color, borderRadius: 8, opacity: lit,
      }} />
    </div>
  );
};
