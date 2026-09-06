import React from "react";
import { AbsoluteFill, CanvasImage, staticFile } from "remotion";
import { z } from "zod";
import { T } from "./theme";

// 채널 바이블: 실패 프레임 + 성공 프레임 좌우 분할 + 한 줄 증상 텍스트
export const ThumbnailSchema = z.object({
  variant: z.enum(["split", "fail-only", "text-first"]),
  failSrc: z.string(),
  fixSrc: z.string(),
  headline: z.string(), // 큰 글씨 (2줄까지, \n)
  sub: z.string(), // 작은 글씨
  badge: z.string(), // 좌상단 배지 (시리즈 이름 등)
  zoom: z.number(), // 프레임 확대 배율 (핵심 부분이 크게 보이도록)
  focusX: z.number(), // 0~1 확대 중심
  focusY: z.number(),
});
type Props = z.infer<typeof ThumbnailSchema>;

const Frame: React.FC<{
  src: string;
  w: number;
  h: number;
  zoom: number;
  fx: number;
  fy: number;
  border: string;
}> = ({ src, w, h, zoom, fx, fy, border }) => (
  <div style={{ width: w, height: h, overflow: "hidden", position: "relative", borderTop: `10px solid ${border}` }}>
    <CanvasImage
      src={staticFile(src)}
      style={{
        position: "absolute",
        width: w * zoom,
        height: (w * zoom * 9) / 16,
        left: -(w * zoom - w) * fx,
        top: -((w * zoom * 9) / 16 - h) * fy,
        objectFit: "cover",
      }}
    />
  </div>
);

const Text: React.FC<{ headline: string; sub: string; align: "left" | "center"; size: number }> = ({
  headline,
  sub,
  align,
  size,
}) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: align === "center" ? "center" : "flex-start", gap: 10 }}>
    {headline.split("\n").map((l, i) => (
      <div
        key={i}
        style={{
          fontFamily: T.sans,
          fontWeight: 700,
          fontSize: size,
          lineHeight: 1.08,
          color: "#fff",
          textShadow: "0 3px 0 rgba(0,0,0,0.85), 0 0 24px rgba(0,0,0,0.8)",
          backgroundColor: i === 0 ? "rgba(229,72,77,0.92)" : "rgba(0,0,0,0.78)",
          padding: "6px 22px",
          borderRadius: 10,
        }}
      >
        {l}
      </div>
    ))}
    {sub !== "" && (
      <div style={{ fontFamily: T.sans, fontWeight: 700, fontSize: size * 0.42, color: T.accent, textShadow: "0 2px 8px #000", marginTop: 6 }}>
        {sub}
      </div>
    )}
  </div>
);

export const Thumbnail: React.FC<Props> = (p) => {
  const W = 1280;
  const H = 720;
  return (
    <AbsoluteFill style={{ backgroundColor: T.bg, width: W, height: H, overflow: "hidden" }}>
      {p.variant === "split" && (
        <>
          <div style={{ display: "flex" }}>
            <Frame src={p.failSrc} w={W / 2} h={H} zoom={p.zoom} fx={p.focusX} fy={p.focusY} border={T.fail} />
            <Frame src={p.fixSrc} w={W / 2} h={H} zoom={p.zoom} fx={p.focusX + 0.12} fy={p.focusY} border={T.ok} />
          </div>
          <div style={{ position: "absolute", left: W / 2 - 3, top: 0, width: 6, height: H, backgroundColor: "#fff" }} />
          <div style={{ position: "absolute", left: 26, top: 22, fontFamily: T.sans, fontWeight: 700, fontSize: 30, color: "#fff", backgroundColor: T.fail, padding: "6px 16px", borderRadius: 8 }}>
            ✕ 실패
          </div>
          <div style={{ position: "absolute", left: W / 2 + 26, top: 22, fontFamily: T.sans, fontWeight: 700, fontSize: 30, color: "#111", backgroundColor: T.ok, padding: "6px 16px", borderRadius: 8 }}>
            ✓ 수정
          </div>
          <div style={{ position: "absolute", left: 40, bottom: 44 }}>
            <Text headline={p.headline} sub={p.sub} align="left" size={84} />
          </div>
        </>
      )}
      {p.variant === "fail-only" && (
        <>
          <Frame src={p.failSrc} w={W} h={H} zoom={p.zoom} fx={p.focusX} fy={p.focusY} border={T.fail} />
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 55%, rgba(0,0,0,0) 100%)" }} />
          <div style={{ position: "absolute", left: 40, top: 40, fontFamily: T.sans, fontWeight: 700, fontSize: 30, color: T.accent, letterSpacing: 4 }}>
            {p.badge}
          </div>
          <div style={{ position: "absolute", left: 40, bottom: 60 }}>
            <Text headline={p.headline} sub={p.sub} align="left" size={96} />
          </div>
          {/* 강조 원 */}
          <div style={{ position: "absolute", left: W * 0.27, top: H * 0.27, width: 300, height: 300, borderRadius: "50%", border: `10px solid ${T.fail}`, boxShadow: "0 0 40px rgba(229,72,77,0.6)" }} />
        </>
      )}
      {p.variant === "text-first" && (
        <>
          <div style={{ position: "absolute", right: 0, top: 0, width: W * 0.5, height: H, display: "flex", flexDirection: "column" }}>
            <Frame src={p.failSrc} w={W * 0.5} h={H / 2} zoom={p.zoom} fx={p.focusX} fy={p.focusY} border={T.fail} />
            <Frame src={p.fixSrc} w={W * 0.5} h={H / 2} zoom={p.zoom} fx={p.focusX + 0.12} fy={p.focusY} border={T.ok} />
          </div>
          <div style={{ position: "absolute", left: 40, top: 44, fontFamily: T.sans, fontWeight: 700, fontSize: 30, color: T.accent, letterSpacing: 4 }}>
            {p.badge}
          </div>
          <div style={{ position: "absolute", left: 40, top: H / 2 - 120, width: W * 0.48 }}>
            <Text headline={p.headline} sub={p.sub} align="left" size={88} />
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};
