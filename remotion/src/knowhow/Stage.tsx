import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { T, EASE_OUT } from "./theme";
import { CaptionChunk } from "./Captions";
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

/* ─────────── 살아 있는 바탕 ───────────
 * 소재 없이 매 프레임 그린다. 정지 이미지를 확대하는 것과 다르다.
 * 참조 영상을 재보면 화면 전체가 같이 움직이지 않고 한쪽 구역만 흐른다.
 * 이루는 것은 셋이다.
 *   격자 — 화면 전체에 촘촘하게. 늘 있고 움직이지 않는다(바닥 역할)
 *   레이저 — 가늘고 밝은 선분이 가장자리에서 미끄러진다. 움직임의 주인공
 *   빛 덩어리 — 뒤에서 천천히 도는 색. 구역마다 밝기가 달라지는 이유
 */
const BLOBS = [
  { c: "#2f6f9e", r: 44, x: 24, y: 26, ax: 12, ay: 7, px: 17, py: 23, o: 0.5 },
  { c: "#245a80", r: 56, x: 74, y: 64, ax: 10, ay: 10, px: 29, py: 19, o: 0.42 },
  { c: "#3f7a62", r: 34, x: 62, y: 70, ax: 15, ay: 6, px: 23, py: 31, o: 0.34 },
];

/** 레이저 선분. axis 를 따라 미끄러진다.
 *  pos  — 축과 직각 방향 위치(%)
 *  from/len — 축 방향 시작·길이(%)
 *  travel — 한 바퀴 도는 데 걸리는 초. 음수면 반대로 */
const LASERS = [
  { axis: "v" as const, pos: 2.0, from: 4, len: 26, c: "#7fdcff", w: 3, travel: 23, o: 0.85 },
  { axis: "h" as const, pos: 30, from: 58, len: 24, c: "#7fdcff", w: 2, travel: -31, o: 0.6 },
  { axis: "v" as const, pos: 84, from: 40, len: 16, c: "#e0a75a", w: 2, travel: 19, o: 0.5 },
  { axis: "h" as const, pos: 54, from: 0, len: 17, c: "#9ad8ff", w: 2, travel: 27, o: 0.4 },
  { axis: "v" as const, pos: 97, from: 55, len: 20, c: "#7fdcff", w: 2, travel: -25, o: 0.35 },
];

export const LiveGround: React.FC<{
  speed?: number;
  grid?: boolean;
  tint?: string;
}> = ({ speed = 1, grid = true, tint = "#080b11" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame / fps) * speed;
  return (
    <AbsoluteFill style={{ backgroundColor: tint, overflow: "hidden" }}>
      {/* 빛 덩어리: 뒤에서 천천히 */}
      {BLOBS.map((b, i) => {
        const x = b.x + b.ax * Math.sin((2 * Math.PI * t) / b.px);
        const y = b.y + b.ay * Math.cos((2 * Math.PI * t) / b.py);
        const pulse = 0.85 + 0.15 * Math.sin((2 * Math.PI * t) / (b.px * 0.61));
        return (
          <div key={i} style={{
            position: "absolute", left: `${x - b.r}%`, top: `${y - b.r}%`,
            width: `${b.r * 2}%`, height: `${b.r * 2}%`,
            background: `radial-gradient(circle, ${b.c} 0%, transparent 68%)`,
            opacity: b.o * pulse, filter: "blur(30px)",
          }} />
        );
      })}

      {/* 격자: 화면 전체에 촘촘하게. 움직이지 않는다 */}
      {grid && (
        <AbsoluteFill style={{
          opacity: 0.17,
          backgroundImage:
            `linear-gradient(rgba(150,205,240,0.55) 1px, transparent 1px),
             linear-gradient(90deg, rgba(150,205,240,0.55) 1px, transparent 1px)`,
          backgroundSize: "52px 52px",
        }} />
      )}

      {/* 레이저: 가늘고 밝은 선분이 미끄러진다 */}
      {LASERS.map((l, i) => {
        const phase = ((t / Math.abs(l.travel)) + i * 0.37) % 1;
        const dir = l.travel > 0 ? phase : 1 - phase;
        // 축을 따라 화면 밖에서 밖으로 지나간다
        const along = -l.len + dir * (100 + l.len * 2);
        const glow = `0 0 12px ${l.c}, 0 0 26px ${l.c}`;
        return l.axis === "v" ? (
          <div key={i} style={{
            position: "absolute", left: `${l.pos}%`, top: `${along}%`,
            width: l.w, height: `${l.len}%`,
            background: `linear-gradient(to bottom, transparent, ${l.c} 22%, ${l.c} 78%, transparent)`,
            boxShadow: glow, opacity: l.o,
          }} />
        ) : (
          <div key={i} style={{
            position: "absolute", top: `${l.pos}%`, left: `${along}%`,
            height: l.w, width: `${l.len}%`,
            background: `linear-gradient(to right, transparent, ${l.c} 22%, ${l.c} 78%, transparent)`,
            boxShadow: glow, opacity: l.o,
          }} />
        );
      })}

      <AbsoluteFill style={{ boxShadow: "inset 0 0 300px 100px rgba(0,0,0,0.7)" }} />
    </AbsoluteFill>
  );
};

/* ─────────── 채널 표식: 매 씬에 붙어 하나의 물건처럼 보이게 ─────────── */
export const Mark: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  return (
    <div style={{
      position: "absolute", right: 56, top: 44, display: "flex", alignItems: "center", gap: 10,
      opacity: 0.55 * ease(frame, fps, 0.2, 0.9),
    }}>
      <div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: T.accent }} />
      <div style={{ fontFamily: T.mono, fontSize: 24, color: T.text, letterSpacing: 3 }}>{text}</div>
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
}> = ({ text, accentWord, align = "left", size = 96, startSec = 0.35 }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const words = text.split(" ");
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, bottom: 300,
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
        display: "flex", flexWrap: "wrap", justifyContent: "center", gap: `2px ${Math.round(fontSize * 0.3)}px`,
        maxWidth, padding: "0 40px",
      }}>
        {ws.map((w, i) => {
          const spoken = t >= w.s - 0.02;
          return (
            <span key={i} style={{
              fontFamily: T.sans, fontSize, fontWeight: 700, lineHeight: 1.34,
              color: spoken ? "#ffffff" : "rgba(255,255,255,0.34)",
              textShadow: "0 3px 14px rgba(0,0,0,0.95), 0 1px 3px rgba(0,0,0,0.9)",
              transition: "none",
            }}>{w.t}</span>
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
