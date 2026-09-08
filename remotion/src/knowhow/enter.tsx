import React from "react";
import { AbsoluteFill } from "remotion";
import { useCue } from "./motion";

/** 전환 종류. 미술이 정한다. `none` 이면 앞 것과 겹치지 않고 그냥 갈린다. */
export type EnterKind = "none" | "slide" | "wipe" | "fade";
export type EnterFrom = "left" | "right" | "up" | "down";

/**
 * 들어오는 씬을 `sec` 동안 움직여 앉힌다. **앞 씬은 그만큼 더 남아 있다**(Episode.tsx 가 늘린다).
 *
 * `TransitionSeries` 를 안 쓴다. 그것은 겹친 만큼 **전체 길이를 줄이는데**, 우리 시각표는
 * 내레이션이 정하고 소리는 절대 시각에 얹힌다 — 화면만 32곳에서 당겨져 소리와 어긋나고
 * 렌더는 안 죽는다. 여기서는 **시각표를 그대로 두고 그림만 겹친다.**
 *
 * 「이어져야 하는 자리」는 `none` 이고 `sec` 0 이다 — 인트로→s00 처럼 같은 그림에서
 * 이어 시작하는 자리에 무엇이든 끼면 그 이음매가 없어진다(연출).
 */
export const Enter: React.FC<{
  sec: number; kind?: EnterKind; from?: EnterFrom; children: React.ReactNode;
}> = ({ sec, kind = "slide", from = "right", children }) => {
  if (sec <= 0 || kind === "none") return <AbsoluteFill>{children}</AbsoluteFill>;
  const p = useCue(0, sec);                       // 0 → 1. spring 이라 앉는 것이 부드럽다
  const off = (1 - p) * 100;
  const style: React.CSSProperties =
    kind === "fade" ? { opacity: p }
    : kind === "wipe" ? { clipPath: from === "left" || from === "right"
        ? `inset(0 ${from === "right" ? off : 0}% 0 ${from === "left" ? off : 0}%)`
        : `inset(${from === "up" ? off : 0}% 0 ${from === "down" ? off : 0}% 0)` }
    : { transform: from === "left" ? `translateX(${-off}%)`
        : from === "right" ? `translateX(${off}%)`
        : from === "up" ? `translateY(${-off}%)` : `translateY(${off}%)` };
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};
