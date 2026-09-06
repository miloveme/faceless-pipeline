import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { T } from "./theme";

export type CaptionChunk = { start: number; end: number; text: string };

// 씬 로컬 시간 기준 자막. offsetSec = 씬 안에서 내레이션이 시작되는 시각(LEAD 0.5s)
export const Captions: React.FC<{
  chunks: CaptionChunk[];
  offsetSec: number;
  maxWidth?: number;
  fontSize?: number;
  bottom?: number;
}> = ({ chunks, offsetSec, maxWidth = 1500, fontSize = 40, bottom = 56 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - offsetSec;
  const cur = chunks.find((c) => t >= c.start - 0.05 && t < c.end + 0.25);
  if (!cur) return null;
  const a = interpolate(t, [cur.start - 0.05, cur.start + 0.1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom,
        display: "flex",
        justifyContent: "center",
        opacity: a,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          fontFamily: T.sans,
          fontSize,
          fontWeight: 700,
          color: "#fff",
          backgroundColor: "rgba(0,0,0,0.72)",
          padding: "10px 26px",
          borderRadius: 10,
          maxWidth,
          textAlign: "center",
          lineHeight: 1.35,
          textShadow: "0 2px 6px rgba(0,0,0,0.6)",
        }}
      >
        {cur.text}
      </div>
    </div>
  );
};
