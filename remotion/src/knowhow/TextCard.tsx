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

export const TextCardSchema = z.object({
  kicker: z.string(), // 작은 윗글 (예: 규칙 / 정리)
  text: z.string(), // 본문. \n 으로 줄바꿈
  variant: z.enum(["rule", "formula", "plain"]),
});

type Props = z.infer<typeof TextCardSchema>;

export const TextCard: React.FC<Props> = ({ kicker, text, variant }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lines = text.split("\n");

  const accentBar = interpolate(frame, [0.2 * fps, 1.0 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE_OUT),
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: variant === "rule" ? T.ruleBg : T.bg,
        justifyContent: "center",
        alignItems: "center",
        fontFamily: T.sans,
      }}
    >
      <div style={{ width: T.contentW }}>
        <div
          style={{
            color: T.accent,
            fontSize: T.fsKicker,
            letterSpacing: 8,
            marginBottom: T.gap,
            opacity: interpolate(frame, [0, 0.5 * fps], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {kicker}
        </div>
        <div
          style={{
            height: 6,
            width: `${accentBar * 120}px`,
            backgroundColor: T.accent,
            marginBottom: 40,
            borderRadius: 3,
          }}
        />
        {lines.map((l, i) => (
          <div
            key={i}
            style={{
              color: T.text,
              fontSize: variant === "formula" ? 64 : 58,
              fontWeight: 700,
              lineHeight: 1.45,
              fontFamily: T.sans,
              letterSpacing: variant === "formula" ? 1 : 0,
              opacity: interpolate(
                frame,
                [(0.4 + i * 0.35) * fps, (0.9 + i * 0.35) * fps],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              ),
              translate: `0px ${interpolate(
                frame,
                [(0.4 + i * 0.35) * fps, (0.9 + i * 0.35) * fps],
                [18, 0],
                {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(...EASE_OUT),
                },
              )}px`,
            }}
          >
            {l}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
