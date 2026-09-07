import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { T, EASE_OUT, faceFor } from "./theme";
import { CaptionChunk, captionRuns } from "./Captions";
import { getGrammar } from "./grammar";

/**
 * 문법 2 · 무대 (stage)
 *
 * 문법 1(패널)과 다른 점은 색이 아니라 화면을 짜는 방식이다.
 *   바탕이 화면을 꽉 채운다 (평평한 단색이 없다)
 *   상자가 없다 (글자가 바탕 위에 그냥 놓인다)
 *   글자가 곧 화면이다 (96px, 좌하단 기준)
 *   자막이 말하는 대로 켜진다 (노래방식)
 *   채널 표식이 우상단에 계속 붙는다
 *
 * 이야기하는 편에 쓴다. 표·로그를 늘어놓는 편에는 패널 문법을 쓴다.
 */

const ease = (frame: number, fps: number, a: number, b: number) =>
  interpolate(frame, [a * fps, b * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(...EASE_OUT),
  });

/** 자막이 앉을 자리·안전영역은 grammars.json 의 stage 항목이 정한다. */
const G = getGrammar("stage");
export const STAGE_CAPTION_BOTTOM = G.caption.bottom;
export const STAGE_SAFE_BOTTOM = G.safeBottom;

/* ─────────── 바탕: 절대 비지 않는다 ─────────── */
export const Ground: React.FC<{
  src?: string;          // 이미지 또는 클립. 없으면 그라데이션 벌판
  kind?: "image" | "video";
  fromSec?: number;
  dim?: number;          // 어둡게 (0~1). 글자가 읽혀야 한다
  drift?: number;        // 아주 느린 확대
  /** 소재를 확대해 잘라낸다. 완성본을 바탕으로 쓰면 그 영상의 번인 자막이 같이 보이는데,
   *  내 자막과 두 겹이 되므로 그 띠를 화면 밖으로 밀어낼 때 쓴다. */
  zoom?: number;
  shiftY?: number;       // 위로 올릴 비율(%). 음수면 아래로
}> = ({ src, kind = "image", fromSec = 0, dim = 0.46, drift = 0.07, zoom = 1, shiftY = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const k = interpolate(frame, [0, durationInFrames], [1, 1 + drift], { extrapolateRight: "clamp" });
  const fade = ease(frame, fps, 0, 0.5);
  return (
    <AbsoluteFill style={{ backgroundColor: "#07080b", overflow: "hidden" }}>
      {src ? (
        <AbsoluteFill style={{ transform: `scale(${k * zoom}) translateY(${shiftY}%)`, opacity: fade }}>
          {kind === "video" ? (
            <Video src={staticFile(src)} trimBefore={Math.round(fromSec * fps)} muted
              style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          )}
        </AbsoluteFill>
      ) : (
        // 소재가 없으면 정지 그라데이션이 아니라 살아 있는 바탕을 깐다
        <AbsoluteFill style={{ opacity: fade }}>
          <LiveGround />
        </AbsoluteFill>
      )}
      {/* 소재를 깐 경우에만 눌러 준다. 살아 있는 바탕은 스스로 어둡고 비네트도 가지고 있어
          여기서 또 덮으면 빛의 움직임이 그만큼 깎인다. */}
      {src && (
        <>
          <AbsoluteFill style={{ backgroundColor: `rgba(7,8,11,${dim})` }} />
          <AbsoluteFill
            style={{ background: "linear-gradient(to top, rgba(7,8,11,0.92) 0%, rgba(7,8,11,0.35) 34%, transparent 62%)" }} />
          <AbsoluteFill
            style={{ boxShadow: "inset 0 0 320px 90px rgba(0,0,0,0.75)", pointerEvents: "none" }} />
        </>
      )}
      {/* 글자가 앉는 아래쪽만 살짝 눌러 준다 */}
      {!src && (
        <AbsoluteFill
          style={{ background: "linear-gradient(to top, rgba(7,8,11,0.72) 0%, rgba(7,8,11,0.2) 26%, transparent 48%)" }} />
      )}
    </AbsoluteFill>
  );
};

/* ─────────── 바탕 ───────────
 * 결이나 무늬를 옅게 깔면 h264 가 어두운 영역에서 그걸 뭉개서
 * 화질이 떨어진 것처럼 보인다. 단색에 위아래 그라데이션만 둔다. */
export const LiveGround: React.FC<{ speed?: number; tint?: string }> = () => (
  <AbsoluteFill style={{
    background: "linear-gradient(180deg, #171b24 0%, #10131a 46%, #0a0c11 100%)",
  }} />
);

/* ─────────── 채널 표식: 매 씬에 붙어 하나의 물건처럼 보이게 ─────────── */
export const Mark: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  return (
    <div style={{
      position: "absolute", right: 56, top: 44, display: "flex", alignItems: "center", gap: 10,
      opacity: 0.55 * ease(frame, fps, 0.2, 0.9),
    }}>
      <div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: T.accent }} />
      <div style={{ fontFamily: faceFor(text), fontSize: 24, color: T.text, letterSpacing: 3 }}>{text}</div>
    </div>
  );
};

/* ─────────── 큰 한 줄. 낱말 하나만 강조할 수 있다 ─────────── */
export const Lead: React.FC<{
  text: string;
  accentWord?: string;
  align?: "left" | "center";
  size?: number;
  startSec?: number;
  /** 화면 아래에서 이 줄까지의 거리(px). 기본 300. 최소는 안전영역(218) — 그 아래는 자막 자리다.
   *  줄을 여러 개 겹치라고 연 것이다 — Lead 를 여러 번 쓰고 bottom 과 startSec 을
   *  달리 주면 한 무대에서 문장이 차례로 쌓인다. 무대 문법은 상자가 없으므로
   *  자리를 겹치지 않게 하는 책임이 연출에게 있다. size 를 보고 간격을 잡는다
   *  (size 96 이면 줄 높이가 약 123px, 최소 간격을 그만큼 둔다). */
  bottom?: number;
}> = ({ text, accentWord, align = "left", size = 96, startSec = 0.35, bottom = 300 }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  if (process.env.NODE_ENV !== "production" && bottom < STAGE_SAFE_BOTTOM) {
    // eslint-disable-next-line no-console
    console.warn(`[Lead] bottom ${bottom} 이 안전영역(${STAGE_SAFE_BOTTOM}) 안이다. 자막을 가린다: "${text}"`);
  }
  const words = text.split(" ");
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, bottom,
      display: "flex", flexWrap: "wrap", gap: `0 ${Math.round(size * 0.26)}px`,
      justifyContent: align === "center" ? "center" : "flex-start",
    }}>
      {words.map((w, i) => {
        const on = ease(frame, fps, startSec + i * 0.085, startSec + 0.55 + i * 0.085);
        const hit = accentWord && w.replace(/[.,]/g, "") === accentWord;
        return (
          <div key={i} style={{
            fontFamily: T.sans, fontSize: size, fontWeight: 700, lineHeight: 1.28,
            color: hit ? "#12141a" : T.text,
            backgroundColor: hit ? T.accent : "transparent",
            padding: hit ? `0 ${Math.round(size * 0.14)}px` : 0,
            borderRadius: hit ? Math.round(size * 0.12) : 0,
            opacity: on,
            transform: `translateY(${(1 - on) * 26}px)`,
            textShadow: hit ? "none" : "0 6px 26px rgba(0,0,0,0.75)",
          }}>{w}</div>
        );
      })}
    </div>
  );
};

/* ─────────── 짧은 줄 몇 개가 차례로. 상자 없음 ─────────── */
export const Beats: React.FC<{ items: string[]; startSec?: number; everySec?: number }> = ({
  items, startSec = 0.5, everySec = 1.6,
}) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  return (
    <div style={{ position: "absolute", left: 120, right: 120, bottom: 290 }}>
      {items.map((it, i) => {
        const on = ease(frame, fps, startSec + i * everySec, startSec + 0.7 + i * everySec);
        return (
          <div key={it} style={{
            display: "flex", alignItems: "center", gap: 26, marginBottom: 30,
            opacity: on, transform: `translateX(${(1 - on) * 30}px)`,
          }}>
            <div style={{ width: 46 * on, height: 3, backgroundColor: T.accent, flexShrink: 0 }} />
            <div style={{
              fontFamily: T.sans, fontSize: 52, fontWeight: 700, color: T.text,
              textShadow: "0 6px 26px rgba(0,0,0,0.8)",
            }}>{it}</div>
          </div>
        );
      })}
    </div>
  );
};

/* ─────────── 노래방식 자막: 말한 낱말만 켜진다 ─────────── */
export const StageCaptions: React.FC<{
  chunks: CaptionChunk[];
  offsetSec: number;
  bottom?: number;
  fontSize?: number;
  maxWidth?: number;
}> = ({ chunks, offsetSec, bottom = STAGE_CAPTION_BOTTOM, fontSize = 44, maxWidth = 1560 }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const t = frame / fps - offsetSec;
  const cur = chunks.find((c) => t >= c.start - 0.05 && t < c.end + 0.25);
  if (!cur) return null;
  const a = interpolate(t, [cur.start - 0.05, cur.start + 0.12], [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // 낱말 시각이 없으면 통째로 켠다 (문법 1과 같은 동작)
  const ws = cur.words ?? [{ s: cur.start, e: cur.end, t: cur.text }];
  return (
    <div style={{
      position: "absolute", left: 0, right: 0, bottom,
      display: "flex", justifyContent: "center", opacity: a, pointerEvents: "none",
    }}>
      <div style={{
        textAlign: "center", maxWidth, padding: "0 40px", lineHeight: 1.34,
        wordBreak: "keep-all",   // 한글이 낱말 중간에서 끊기지 않게
      }}>
        {captionRuns(ws).map((run, ri) => {
          // 상자는 그 구의 첫 낱말에서 켜진다. 켜지기 전에는 보통 낱말과 똑같이 보여야 한다 —
          // 상자 안에서 읽힐 어두운 색을 미리 쓰면 어두운 바탕에 묻혀 문장에 구멍이 난다.
          const boxOn = run.hl && t >= run.words[0].s - 0.02;
          const body = run.words.map((w, i) => {
            const spoken = t >= w.s - 0.02;
            const color = boxOn
              ? (spoken ? "#12141a" : "rgba(18,20,26,0.45)")
              : (spoken ? "#ffffff" : "rgba(255,255,255,0.34)");
            return <span key={i} style={{ color }}>{i ? " " : ""}{w.t}</span>;
          });
          return (
            <span key={ri} style={{
              fontFamily: T.sans, fontSize, fontWeight: 700, lineHeight: 1.34,
              backgroundColor: boxOn ? T.accent : "transparent",
              // 여백을 늘 잡아 둔다. 켜질 때 생기면 줄 폭이 변해 문장 전체가 옆으로 튄다.
              padding: run.hl ? "2px 10px" : 0,
              borderRadius: 8,
              textShadow: boxOn ? "none" : "0 3px 14px rgba(0,0,0,0.95), 0 1px 3px rgba(0,0,0,0.9)",
            }}>{body}</span>
          );
        })}
      </div>
    </div>
  );
};

/* ─────────── 무대 한 판 ─────────── */
export const Stage: React.FC<{
  ground?: { src?: string; kind?: "image" | "video"; fromSec?: number; dim?: number; zoom?: number; shiftY?: number };
  mark?: string;
  children?: React.ReactNode;
}> = ({ ground = {}, mark = "J Note", children }) => (
  <AbsoluteFill>
    <Ground {...ground} />
    {children}
    {mark !== "" && <Mark text={mark} />}
  </AbsoluteFill>
);
