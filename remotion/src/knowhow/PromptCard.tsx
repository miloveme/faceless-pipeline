import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { T, EASE_OUT } from "./theme";

export const SegmentType = z.enum([
  "plain", // 기본
  "hl", // 노란 하이라이트
  "del", // 빨간 취소선 (diff 삭제)
  "add", // 초록 (diff 추가)
  "dim", // 흐리게
  "label", // 소제목 줄 (BEFORE / AFTER)
  "br", // 줄바꿈
]);

export const PromptCardSchema = z.object({
  title: z.string(),
  segments: z.array(z.object({ t: z.string(), type: SegmentType })),
  reveal: z.enum(["none", "sequential", "typing"]),
  revealEverySec: z.number(), // sequential: 세그먼트 간격
  charsPerSec: z.number(), // typing 속도
  strikeAtSec: z.number(), // typing: 이 시각부터 취소선 (0 = 없음)
  fontSize: z.number(),
});

type Props = z.infer<typeof PromptCardSchema>;

const segStyle = (
  type: Props["segments"][number]["type"],
): React.CSSProperties => {
  switch (type) {
    case "hl":
      return {
        color: T.accent,
        backgroundColor: "rgba(245,185,66,0.16)",
        borderRadius: 6,
        padding: "0 6px",
        boxDecorationBreak: "clone",
      };
    case "del":
      return {
        color: T.fail,
        textDecoration: "line-through",
        textDecorationThickness: 4,
        opacity: 0.9,
      };
    case "add":
      return {
        color: T.ok,
        backgroundColor: "rgba(62,207,142,0.12)",
        borderRadius: 6,
        padding: "0 6px",
        boxDecorationBreak: "clone",
      };
    case "dim":
      return { color: T.muted, opacity: 0.45 };
    case "label":
      return {
        display: "block",
        color: T.muted,
        fontFamily: T.sans,
        fontSize: "0.72em",
        letterSpacing: 4,
        marginTop: "0.9em",
        marginBottom: "0.25em",
      };
    default:
      return { color: T.text };
  }
};

export const PromptCard: React.FC<Props> = ({
  title,
  segments,
  reveal,
  revealEverySec,
  charsPerSec,
  strikeAtSec,
  fontSize,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardIn = interpolate(frame, [0, 0.6 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE_OUT),
  });

  // 순차 등장: label/br 은 순서 계산에서 제외
  let revealIdx = 0;
  const typedTotal = Math.floor((frame / fps) * charsPerSec);
  let typedUsed = 0;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: T.bg,
        justifyContent: "center",
        alignItems: "center",
        fontFamily: T.mono,
      }}
    >
      <div
        style={{
          width: 1600,
          backgroundColor: T.panel,
          border: `2px solid ${T.panelLine}`,
          borderRadius: 24,
          padding: "48px 64px",
          opacity: cardIn,
          translate: `0px ${(1 - cardIn) * 24}px`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
        }}
      >
        <div
          style={{
            fontFamily: T.sans,
            color: T.muted,
            fontSize: 30,
            letterSpacing: 6,
            marginBottom: 28,
          }}
        >
          {title}
        </div>
        <div style={{ fontSize, lineHeight: 1.55, color: T.text }}>
          {segments.map((s, i) => {
            if (s.type === "br") return <br key={i} />;
            const countsForReveal = s.type !== "label";
            const myIdx = countsForReveal ? revealIdx++ : -1;

            let opacity = 1;
            if (reveal === "sequential" && countsForReveal) {
              opacity = interpolate(
                frame,
                [
                  myIdx * revealEverySec * fps,
                  myIdx * revealEverySec * fps + 0.5 * fps,
                ],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              );
            }

            let text = s.t;
            if (reveal === "typing" && countsForReveal) {
              const remain = Math.max(0, typedTotal - typedUsed);
              text = s.t.slice(0, remain);
              typedUsed += s.t.length;
            }

            const strikeW =
              reveal === "typing" && strikeAtSec > 0
                ? interpolate(
                    frame,
                    [strikeAtSec * fps, strikeAtSec * fps + 0.5 * fps],
                    [0, 100],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                  )
                : 0;

            return (
              <span
                key={i}
                style={{
                  ...segStyle(s.type),
                  opacity: opacity * Number(segStyle(s.type).opacity ?? 1),
                  position: "relative",
                  whiteSpace: "pre-wrap",
                }}
              >
                {text}
                {reveal === "typing" &&
                  countsForReveal &&
                  text.length < s.t.length && (
                    <span style={{ color: T.accent }}>▍</span>
                  )}
                {strikeW > 0 && countsForReveal && (
                  <span
                    style={{
                      position: "absolute",
                      left: 0,
                      top: "52%",
                      height: 6,
                      width: `${strikeW}%`,
                      backgroundColor: T.fail,
                      borderRadius: 3,
                    }}
                  />
                )}
              </span>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
