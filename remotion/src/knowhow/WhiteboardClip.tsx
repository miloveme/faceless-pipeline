import React from "react";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { z } from "zod";
import { T } from "./theme";

// srt-whiteboard-animation 스킬이 만든 미색 종이 손그림 mp4를 어두운 채널 톤 위에 얹는다.
// 스킬 렌더는 반드시 --no-subtitles (자막은 Captions가 그린다).
export const WhiteboardClipSchema = z.object({
  src: z.string(),              // public 기준 경로
  kicker: z.string(),           // 좌상단 라벨 (자막 안전영역 밖)
  fromSec: z.number(),          // 클립 안에서 시작할 지점
  fit: z.enum(["frame", "full"]),
});
type Props = z.infer<typeof WhiteboardClipSchema>;

export const WhiteboardClip: React.FC<Props> = ({ src, kicker, fromSec, fit }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // 미색 종이가 어두운 화면에서 갑자기 튀지 않도록 0.35초 페이드
  const fade = interpolate(frame, [0, T.fade * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const framed = fit === "frame";
  return (
    <AbsoluteFill style={{ backgroundColor: T.bg }}>
      <div
        style={{
          position: "absolute",
          inset: framed ? "112px 96px 168px 96px" : 0,   // 하단은 자막 안전영역만큼 더 비운다
          borderRadius: framed ? 18 : 0,
          overflow: "hidden",
          opacity: fade,
          boxShadow: framed ? "0 24px 60px rgba(0,0,0,0.55)" : "none",
        }}
      >
        <Video
          src={staticFile(src)}
          trimBefore={Math.round(fromSec * fps)}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
      {kicker !== "" && (
        <div
          style={{
            position: "absolute", left: 96, top: 48,
            fontFamily: T.sans, fontSize: T.fsKicker, fontWeight: 700, letterSpacing: 2,
            color: T.accent, opacity: fade,
          }}
        >
          {kicker}
        </div>
      )}
    </AbsoluteFill>
  );
};
