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
 *
 * 무엇으로 만드느냐가 중요하다. 다른 채널의 화면을 재서 그 장치(격자·레이저·청록)를
 * 옮겨 오면 그 채널처럼 보인다. 그래서 이 채널의 것으로 만든다.
 *   시간 눈금 — 이 공정의 뼈대가 "음성 길이가 영상 길이를 정한다"이다
 *   파형 띠   — 이 채널은 음성과 음악에서 왔다
 *   호박색    — theme 의 accent. 남의 팔레트를 가져오지 않는다
 */

/** 결정적 의사난수. 프레임마다 같은 모양이 나와야 한다(랜덤을 쓰면 화면이 지직거린다). */
const rnd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** 파형 한 줄. 시간에 따라 옆으로 흐른다. */
const waveBand = (t: number, n: number, seed: number) => {
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    const k = i + seed * 1000;
    // 봉우리 몇 개가 겹쳐 사람 목소리 같은 들쭉날쭉함이 나오게
    const amp =
      (0.35 + 0.65 * rnd(k)) *
      (0.5 + 0.5 * Math.sin(u * Math.PI * 3 + t * 0.35 + seed)) *
      (0.4 + 0.6 * Math.sin(u * Math.PI * 11 + seed * 3));
    pts.push(`${(u * 100).toFixed(2)},${(50 - amp * 46).toFixed(2)}`);
  }
  for (let i = n; i >= 0; i--) {
    const u = i / n;
    const k = i + seed * 1000;
    const amp =
      (0.35 + 0.65 * rnd(k)) *
      (0.5 + 0.5 * Math.sin(u * Math.PI * 3 + t * 0.35 + seed)) *
      (0.4 + 0.6 * Math.sin(u * Math.PI * 11 + seed * 3));
    pts.push(`${(u * 100).toFixed(2)},${(50 + amp * 46).toFixed(2)}`);
  }
  return pts.join(" ");
};

export const LiveGround: React.FC<{
  speed?: number;
  tint?: string;
}> = ({ speed = 1, tint = "#0c0d10" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame / fps) * speed;

  // 시간 눈금: 일정 간격의 세로 실선. 통째로 아주 느리게 흐른다.
  const TICK = 46;                       // px
  const shift = ((t * 5.5) % TICK) - TICK;

  return (
    <AbsoluteFill style={{ backgroundColor: tint, overflow: "hidden" }}>
      {/* 바탕 색조 — 채널 강조색을 아주 옅게 깔아 중립 회색을 면한다 */}
      <AbsoluteFill style={{
        background: `radial-gradient(130% 100% at 50% 6%, rgba(245,185,66,0.035) 0%, rgba(14,14,16,0.5) 40%, ${tint} 100%)`,
      }} />

      {/* 시간 눈금 */}
      <AbsoluteFill style={{
        opacity: 0.075,
        transform: `translateX(${shift}px)`,
        backgroundImage: `linear-gradient(90deg, rgba(245,185,66,0.9) 1px, transparent 1px)`,
        backgroundSize: `${TICK}px 100%`,
        maskImage: "linear-gradient(to bottom, #000 0%, rgba(0,0,0,0.35) 42%, transparent 78%)",
      }} />
      {/* 다섯 칸마다 긴 눈금 하나 */}
      <AbsoluteFill style={{
        opacity: 0.115,
        transform: `translateX(${shift}px)`,
        backgroundImage: `linear-gradient(90deg, rgba(245,185,66,1) 1px, transparent 1px)`,
        backgroundSize: `${TICK * 5}px 100%`,
        maskImage: "linear-gradient(to bottom, #000 0%, rgba(0,0,0,0.5) 55%, transparent 88%)",
      }} />

      {/* 파형 띠 둘 — 아래쪽에 낮게 깔린다. 글자를 방해하지 않는 밝기 */}
      {[
        { y: 71, h: 17, o: 0.042, sp: 1.0, seed: 1 },
        { y: 80, h: 12, o: 0.028, sp: 0.62, seed: 2 },
      ].map((w, i) => (
        <svg key={i} viewBox="0 0 100 100" preserveAspectRatio="none"
          style={{
            position: "absolute", left: `${-8 + Math.sin(t * 0.06 * w.sp + i) * 3}%`,
            top: `${w.y}%`, width: "116%", height: `${w.h}%`, opacity: w.o,
          }}>
          <polygon points={waveBand(t * w.sp, 150, w.seed)} fill="#f5b942" />
        </svg>
      ))}

      {/* 지금 지나는 자리 — 재생 헤드처럼 한 줄이 천천히 오른쪽으로 */}
      <div style={{
        position: "absolute", top: 0, bottom: 0,
        left: `${((t * 1.1) % 118) - 9}%`,
        width: 2,
        background: "linear-gradient(to bottom, transparent, rgba(245,185,66,0.42) 30%, rgba(245,185,66,0.42) 70%, transparent)",
        opacity: 0.5,
      }} />

      <AbsoluteFill style={{ boxShadow: "inset 0 0 170px 40px rgba(0,0,0,0.55)" }} />
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
          const hl = w.hl && spoken;
          return (
            <span key={i} style={{
              fontFamily: T.sans, fontSize, fontWeight: 700, lineHeight: 1.34,
              color: hl ? "#12141a" : spoken ? "#ffffff" : "rgba(255,255,255,0.34)",
              backgroundColor: hl ? T.accent : "transparent",
              padding: hl ? "2px 10px" : 0,
              borderRadius: 8,
              textShadow: hl ? "none" : "0 3px 14px rgba(0,0,0,0.95), 0 1px 3px rgba(0,0,0,0.9)",
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
