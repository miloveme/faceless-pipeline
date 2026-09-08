import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { T, EASE_OUT, faceFor } from "./theme";
import { getGrammar } from "./grammar";

/**
 * 패널 문법의 담기 — 씬 하나가 카드 한 장 안에 든다.
 *
 * **여기 편별 값이 하나도 없다.** 전부 토큰과 문법에서 온다. 그래서 편 폴더가 아니라 여기 있다 —
 * 편 안에 두면 편마다 복사되고, **토큰이 있어도 편마다 상자를 다시 짠다.**
 * 실제로 그렇게 해서 카드 안쪽 크기를 셋이 각자 계산했고 셋 다 틀렸다.
 */
export const Panel: React.FC<{ kicker?: string; children: React.ReactNode; grammar?: string }> = ({
  kicker, children, grammar = "panel",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = interpolate(frame, [0, 0.4 * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(...EASE_OUT),
  });
  return (
    <AbsoluteFill style={{ backgroundColor: T.bg, fontFamily: T.sans }}>
      <div
        style={{
          position: "absolute", left: T.edge, right: T.edge, top: T.edge, bottom: getGrammar(grammar).safeBottom,
          backgroundColor: T.panel, border: `${T.lineW}px solid ${T.panelLine}`, borderRadius: T.radius,
          padding: T.pad, opacity: fade, display: "flex", flexDirection: "column", gap: T.gap,
          overflow: "hidden",
        }}
      >
        {kicker !== undefined && kicker !== "" && (
          <div style={{ color: T.accent, fontSize: T.fsKicker, letterSpacing: 6, fontFamily: faceFor(kicker) }}>
            {kicker}
          </div>
        )}
        {children}
      </div>
    </AbsoluteFill>
  );
};

/**
 * 카드 **안쪽** 크기. 조판이 쓸 수 있게 `Panel` 이 계산해서 내준다.
 *
 * **적어 두지 않는다.** 네 값에서 나오는 값이라 하나가 바뀌면 적어 둔 숫자가 조용히 틀린다 —
 * 특히 `safeBottom` 은 문법마다 달라서(panel 218 · workshop 232) 한 숫자로는 한 문법만 맞는다.
 * `lineW` 를 빼먹으면 한 변에 4px 이 는다. 그게 셋이 세 번 틀린 자리다.
 */
export const panelInner = (grammar = "panel") => {
  const inset = 2 * (T.lineW + T.pad);
  return {
    w: 1920 - 2 * T.edge - inset,
    h: 1080 - T.edge - getGrammar(grammar).safeBottom - inset,
  };
};
