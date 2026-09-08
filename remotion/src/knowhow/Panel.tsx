import React from "react";
import { AbsoluteFill } from "remotion";
import { T, faceFor } from "./theme";
import { getGrammar } from "./grammar";
import { useCue } from "./motion";

/**
 * 씬 하나를 담는 자리. **어떻게 담을지는 문법의 `contain` 이 정한다.**
 *
 *   card   상자를 두른다. 그 안쪽만큼 소재가 줄어든다
 *   none   상자가 없다. 소재가 화면을 직접 쓴다
 *
 * **여기 편별 값이 하나도 없다.** 전부 토큰과 문법에서 온다. 그래서 편 폴더가 아니라 여기 있다 —
 * 편 안에 두면 편마다 복사되고, 토큰이 있어도 편마다 상자를 다시 짠다.
 * 실제로 그렇게 해서 카드 안쪽 크기를 셋이 각자 계산했고 셋 다 틀렸다.
 */

/** 담기가 먹는 여백. **`panelInner` 와 `Panel` 이 이 하나를 같이 본다** — 둘이 따로 계산하면
 *  그린 상자와 알려 주는 안쪽 크기가 갈리고, 그건 아무도 안 잰다. */
const insetOf = (grammar: string) => {
  const kind = getGrammar(grammar).contain.kind;
  if (kind === "none") return 0;
  if (kind === "card") return T.lineW + T.pad;
  // 다른 담기(예: workshop 의 window)는 **여백이 여기서 안 나온다** — 그 부품이 자기 자리를 갖는다.
  // 그때 card 로 쳐서 숫자를 돌려주면 조용히 틀린 값이 나가고 아무도 안 잰다.
  throw new Error(
    `Panel: 담기 "${kind}" 는 여기서 안 그립니다(문법 ${grammar}). ` +
    `window 는 Workshop.tsx 의 WIN 이 자리를 정합니다 — 그 부품에서 크기를 받으세요.`);
};

export const Panel: React.FC<{ kicker?: string; children: React.ReactNode; grammar?: string }> = ({
  kicker, children, grammar = "panel",
}) => {
  const fade = useCue(0, 0.4);
  const boxed = getGrammar(grammar).contain.kind !== "none";
  return (
    <AbsoluteFill style={{ backgroundColor: T.bg, fontFamily: T.sans }}>
      <div
        style={{
          position: "absolute", left: T.edge, right: T.edge, top: T.edge,
          bottom: getGrammar(grammar).safeBottom, opacity: fade,
          display: "flex", flexDirection: "column", gap: T.gap, overflow: "hidden",
          ...(boxed
            ? { backgroundColor: T.panel, border: `${T.lineW}px solid ${T.panelLine}`,
                borderRadius: T.radius, padding: T.pad }
            : {}),
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
 * 씬이 실제로 쓸 수 있는 **안쪽** 크기. 조판이 이 값을 읽어 쓴다.
 *
 * **적어 두지 않는다.** 다섯 값에서 나오는 값이라 하나가 바뀌면 적어 둔 숫자가 조용히 틀린다.
 * 그리고 **무엇이 입력인지를 다 세어야 한다** — 처음에는 `safeBottom` 만 문법에서 받고
 * `contain` 은 상수처럼 굳어 있었다. 그래서 상자가 없는 문법에서 **있지도 않은 상자만큼
 * 116px 을 뺐고**, 상자를 뺀 이득 24.3% 가 계산에서 사라졌다.
 * 식으로 옮기는 것만으로는 부족하다. 식이 좁으면 입력이 바뀌어도 안 따라온다.
 */
export const panelInner = (grammar = "panel") => {
  const inset = 2 * insetOf(grammar);
  return {
    w: 1920 - 2 * T.edge - inset,
    h: 1080 - T.edge - getGrammar(grammar).safeBottom - inset,
  };
};
