import React from "react";
import {
  AbsoluteFill,
  CanvasImage,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { T, EASE_OUT } from "./theme";

// 정지 이미지 카드: 단독(컨택트 시트 등) 또는 좌우 쌍(전후 비교)
export const ImageCardSchema = z.object({
  mode: z.enum(["single", "pair"]),
  src: z.string(),
  src2: z.string(),
  label: z.string(),
  label2: z.string(),
  caption: z.string(),
  kenBurns: z.boolean(), // 아주 느린 확대
  arrowText: z.string(), // pair 모드에서 두 이미지 사이 문구 ("" 이면 없음)
});

type Props = z.infer<typeof ImageCardSchema>;

export const ImageCard: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE_OUT),
  });
  const kb = p.kenBurns
    ? interpolate(frame, [0, durationInFrames], [1, 1.06], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  const Img: React.FC<{ src: string; w: number; label: string }> = ({
    src,
    w,
    label,
  }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
      {label !== "" && (
        <div style={{ fontFamily: T.sans, fontSize: 32, color: T.muted, letterSpacing: 2 }}>
          {label}
        </div>
      )}
      <div
        style={{
          width: w,
          overflow: "hidden",
          borderRadius: 16,
          border: `2px solid ${T.panelLine}`,
          backgroundColor: "#000",
        }}
      >
        <CanvasImage
          src={staticFile(src)}
          style={{ width: w, display: "block", scale: String(kb), transformOrigin: "center" }}
        />
      </div>
    </div>
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: T.bg,
        justifyContent: "center",
        alignItems: "center",
        opacity: fadeIn,
      }}
    >
      {p.mode === "single" ? (
        <Img src={p.src} w={1760} label={p.label} />
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: 36 }}>
          <Img src={p.src} w={840} label={p.label} />
          {p.arrowText !== "" && (
            <div
              style={{
                fontFamily: T.sans,
                color: T.accent,
                fontSize: 30,
                fontWeight: 700,
                textAlign: "center",
                width: 120,
                lineHeight: 1.3,
              }}
            >
              {p.arrowText}
            </div>
          )}
          <Img src={p.src2} w={840} label={p.label2} />
        </div>
      )}
      {p.caption !== "" && (
        <div
          style={{
            position: "absolute",
            top: 48,
            fontFamily: T.sans,
            fontSize: 36,
            color: T.text,
            backgroundColor: "rgba(23,26,33,0.85)",
            padding: "12px 28px",
            borderRadius: 12,
            border: `1px solid ${T.panelLine}`,
          }}
        >
          {p.caption}
        </div>
      )}
    </AbsoluteFill>
  );
};
