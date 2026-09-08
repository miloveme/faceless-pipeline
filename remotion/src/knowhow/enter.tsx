import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * 들어오는 씬을 `sec` 동안 밀어 넣는다. **앞 씬은 그만큼 더 남아 있다**(Episode.tsx 가 늘린다).
 *
 * `TransitionSeries` 를 안 쓴다. 그것은 겹친 만큼 **전체 길이를 줄이는데**, 우리 시각표는
 * 내레이션이 정하고 소리는 절대 시각에 얹힌다 — 화면만 32곳에서 당겨져 소리와 어긋나고
 * 렌더는 안 죽는다. 여기서는 **시각표를 그대로 두고 그림만 겹친다.**
 *
 * **종류는 하나(`slide`)이고 길이와 축만 다르다**(연출·미술). 규칙을 하나만 배우면 된다.
 * ```
 *  0f   이어져야 하는 자리.   아무것도 안 한다
 *  6f   짝 안.               오른쪽 → 왼쪽
 * 10f   일반.                오른쪽 → 왼쪽
 * 15f   절 사이.             아래 → 위
 * ```
 * **한때 「6f 는 바뀌는 요소만 민다」였는데 폐기됐다** — 요소만 밀려면 두 씬이 같은 배치를
 * 공유해야 하는데 카드가 갈리는 자리(prompt → inout)에는 공유할 배치가 없다. 성립하지 않는 값이었다.
 * **무엇이 밀리는지는 문법의 `unit` 이 정한다** — `episode`(바탕·자막·서명)는 안 밀고
 * `scene`(담기·글)은 민다. Episode.tsx 가 자막을 이 밖에 두는 이유가 그것이다.
 *
 * 이징은 `Easing.out(Easing.cubic)` 이다. 테마의 `EASE_OUT`(0.16,1,0.3,1)을 밀기에 쓰면
 * 1920px 을 0.2초에 밀 때 **첫 프레임에 1,317px(화면의 69%)** 이 지나가 「컷 + 안착」으로 보인다.
 * `EASE_OUT` 은 제자리에 나타나는 요소용으로 남는다.
 */
const GRADE = (sec: number) =>
  sec <= 0 ? null                          // 이어져야 하는 자리
  : sec < 0.42 ? ("left" as const)         // 6f · 10f — 오른쪽에서 들어와 왼쪽으로. 길이만 다르다
  : ("up" as const);                       // 15f — 아래에서 올라온다

export const Enter: React.FC<{ sec: number; children: React.ReactNode }> = ({ sec, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dir = GRADE(sec);
  if (dir === null) return <AbsoluteFill>{children}</AbsoluteFill>;
  const p = interpolate(frame, [0, Math.round(sec * fps)], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
  });
  const off = (1 - p) * 100;
  return (
    <AbsoluteFill style={{ transform: dir === "left" ? `translateX(${off}%)` : `translateY(${off}%)` }}>
      {children}
    </AbsoluteFill>
  );
};
