import React from "react";
import {
  AbsoluteFill,
  CanvasImage,
  Easing,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Video } from "@remotion/media";
import { z } from "zod";
import { T, EASE_OUT } from "./theme";

export const SplitCompareSchema = z.object({
  leftSrc: z.string(),
  rightSrc: z.string(),
  leftStill: z.string(), // pauseAt 시각의 정지 프레임 (ffmpeg로 미리 추출)
  rightStill: z.string(),
  leftLabel: z.string(),
  rightLabel: z.string(),
  pauseAtSec: z.number(), // 이 시각에 정지 후 확대
  zoomLeft: z.object({ x: z.number(), y: z.number(), w: z.number(), h: z.number() }), // 0~1 비율
  zoomRight: z.object({ x: z.number(), y: z.number(), w: z.number(), h: z.number() }),
  zoomSec: z.number(), // 확대에 걸리는 시간
  clipSec: z.number(), // 원본 클립 길이
});

type Props = z.infer<typeof SplitCompareSchema>;

const PANE_W = 920;
const PANE_H = Math.round((PANE_W * 9) / 16);

const Pane: React.FC<{
  src: string;
  still: string;
  label: string;
  color: string;
  pauseAtSec: number;
  zoom: Props["zoomLeft"];
  zoomSec: number;
}> = ({ src, still, label, color, pauseAtSec, zoom, zoomSec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pauseF = Math.round(pauseAtSec * fps);

  // 확대: 지정 영역이 화면을 채우도록 scale/translate
  const s = interpolate(frame, [pauseF + 0.4 * fps, pauseF + (0.4 + zoomSec) * fps], [1, 1 / zoom.w], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE_OUT),
  });
  const cx = (zoom.x + zoom.w / 2) * PANE_W;
  const cy = (zoom.y + zoom.h / 2) * PANE_H;
  const tx = (PANE_W / 2 - cx) * (s - 1);
  const ty = (PANE_H / 2 - cy) * (s - 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div
        style={{
          fontFamily: T.sans,
          fontSize: 34,
          fontWeight: 700,
          color,
          letterSpacing: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          width: PANE_W,
          height: PANE_H,
          overflow: "hidden",
          borderRadius: T.radius,
          border: `3px solid ${color}`,
          backgroundColor: "#000",
          position: "relative",
        }}
      >
        <Sequence durationInFrames={pauseF} layout="none">
          <Video
            src={staticFile(src)}
            muted
            style={{ width: PANE_W, height: PANE_H, objectFit: "cover" }}
          />
        </Sequence>
        <Sequence from={pauseF} layout="none">
          <CanvasImage
            src={staticFile(still)}
            style={{
              width: PANE_W,
              height: PANE_H,
              objectFit: "cover",
              transformOrigin: "center",
              scale: String(s),
              translate: `${tx / s}px ${ty / s}px`,
            }}
          />
        </Sequence>
      </div>
    </div>
  );
};

export const SplitCompare: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pauseF = Math.round(p.pauseAtSec * fps);
  const tSec = Math.min(frame, pauseF) / fps;

  const pauseBadge = interpolate(frame, [pauseF, pauseF + 0.3 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{ backgroundColor: T.bg, justifyContent: "center", alignItems: "center" }}
    >
      <div style={{ display: "flex", gap: 40 }}>
        <Pane
          src={p.leftSrc}
          still={p.leftStill}
          label={p.leftLabel}
          color={T.fail}
          pauseAtSec={p.pauseAtSec}
          zoom={p.zoomLeft}
          zoomSec={p.zoomSec}
        />
        <Pane
          src={p.rightSrc}
          still={p.rightStill}
          label={p.rightLabel}
          color={T.ok}
          pauseAtSec={p.pauseAtSec}
          zoom={p.zoomRight}
          zoomSec={p.zoomSec}
        />
      </div>
      <div
        style={{
          position: "absolute",
          top: 60,
          fontFamily: T.mono,
          fontSize: 34,
          color: T.muted,
          letterSpacing: 2,
        }}
      >
        {tSec.toFixed(1)}s / {p.clipSec.toFixed(0)}s
        <span
          style={{
            marginLeft: 24,
            color: T.accent,
            opacity: pauseBadge,
          }}
        >
          ⏸ {p.pauseAtSec.toFixed(0)}초 정지 · 확대
        </span>
      </div>
    </AbsoluteFill>
  );
};
