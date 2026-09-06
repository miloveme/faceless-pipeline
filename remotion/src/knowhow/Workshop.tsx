import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { T, EASE_OUT } from "./theme";
import { CaptionChunk } from "./Captions";
import { getGrammar } from "./grammar";
import { LiveGround } from "./Stage";

/**
 * 문법 3 · 작업실 (workshop)
 *
 * 담기로 보면 세 문법이 이렇게 갈린다.
 *   패널 — 카드마다 상자
 *   무대 — 상자 없음
 *   작업실 — 편 전체가 하나의 상자
 *
 * 화면이 곧 작업실이다. 창틀이 매 씬에 계속 붙어 있고 그 안에서 내용만 갈린다.
 * 안에 들어가는 건 다시 그린 카드가 아니라 실제 화면·실제 로그다.
 * 자막은 창 밖 책상 위에 앉는다. 창 안은 작업물이므로 건드리지 않는다.
 *
 * 도구를 실제로 굴린 기록을 보여주는 편에 쓴다.
 */

const ease = (frame: number, fps: number, a: number, b: number) =>
  interpolate(frame, [a * fps, b * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(...EASE_OUT),
  });

/** 창 바깥 치수. 자막은 창 아래 책상에 앉으므로 여기서 정해진다. */
// 창 바깥 치수. 아래는 문법의 안전영역과 같아야 자막이 창을 안 가린다.
export const WIN = { left: 96, right: 96, top: 96, bottom: getGrammar("workshop").safeBottom };
const G = getGrammar("workshop");
export const WORKSHOP_CAPTION_BOTTOM = G.caption.bottom;
const TITLE_H = 56;   // 제목 표시줄
const PAD = 22;       // 창 안쪽 여백
const CMD_H = 51;     // "$ 명령" 줄

/* ─────────── 책상: 창을 올려 둘 바닥 ─────────── */
// 창을 올려 둘 바닥. 다른 문법의 바탕과 같은 것을 써야 씬이 갈려도 한 편으로 읽힌다.
const Desk: React.FC = () => <LiveGround speed={0.55} />;

/* ─────────── 창틀: 편 전체에 계속 붙는 하나의 상자 ───────────
 * 내용이 무엇이냐에 따라 창을 갈아 끼운다.
 *   terminal — 명령을 돌린 기록 (제목만 가운데)
 *   browser  — 웹에 있는 것 (뒤로/앞으로 + 주소 알약)
 * 창 종류가 곧 "지금 어디서 벌어지는 일인가"를 말해 준다. */
export type Chrome = "terminal" | "browser";

const Dots: React.FC = () => (
  <>
    {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
      <div key={c} style={{ width: 13, height: 13, borderRadius: 7, backgroundColor: c, flexShrink: 0 }} />
    ))}
  </>
);

const TitleBar: React.FC<{ chrome: Chrome; title: string }> = ({ chrome, title }) => {
  if (chrome === "browser") {
    return (
      <div style={{
        height: 60, flexShrink: 0, display: "flex", alignItems: "center", gap: 13,
        padding: "0 18px", backgroundColor: "#12151b", borderBottom: `1px solid ${T.panelLine}`,
      }}>
        <Dots />
        <div style={{ marginLeft: 8, display: "flex", gap: 14, color: T.muted, fontSize: 24, flexShrink: 0 }}>
          <span>‹</span><span>›</span>
        </div>
        {/* 주소 알약 */}
        <div style={{
          marginLeft: 6, flex: 1, height: 34, borderRadius: 17, backgroundColor: "#0b0d11",
          border: `1px solid ${T.panelLine}`, display: "flex", alignItems: "center", gap: 10,
          padding: "0 16px", fontFamily: T.mono, fontSize: 22, color: T.text, letterSpacing: 0.5,
        }}>
          <div style={{
            width: 11, height: 9, borderRadius: 2, border: `2px solid ${T.ok}`,
            borderTopLeftRadius: 6, borderTopRightRadius: 6, flexShrink: 0,
          }} />
          {title}
        </div>
      </div>
    );
  }
  // terminal — 제목만 가운데. 주소 알약도 화살표도 없다.
  return (
    <div style={{
      height: 56, flexShrink: 0, display: "flex", alignItems: "center", gap: 13,
      padding: "0 18px", backgroundColor: "#161a21", borderBottom: `1px solid ${T.panelLine}`,
      position: "relative",
    }}>
      <Dots />
      <div style={{
        position: "absolute", left: 0, right: 0, textAlign: "center",
        fontFamily: T.mono, fontSize: 22, color: T.muted, letterSpacing: 1, pointerEvents: "none",
      }}>{title}</div>
    </div>
  );
};

export const Win: React.FC<{
  chrome?: Chrome;
  title: string;
  children: React.ReactNode;
}> = ({ chrome = "terminal", title, children }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const on = ease(frame, fps, 0, 0.45);
  return (
    <AbsoluteFill>
      <Desk />
      <div
        style={{
          position: "absolute",
          left: WIN.left, right: WIN.right, top: WIN.top, bottom: WIN.bottom,
          borderRadius: 14,
          overflow: "hidden",
          backgroundColor: chrome === "terminal" ? "#0a0c10" : "#0b0d11",
          border: `1px solid ${T.panelLine}`,
          boxShadow: "0 40px 90px rgba(0,0,0,0.65)",
          opacity: on,
          transform: `translateY(${(1 - on) * 14}px)`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <TitleBar chrome={chrome} title={title} />
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>{children}</div>
      </div>
    </AbsoluteFill>
  );
};

/* ─────────── 창 안: 실제 로그가 한 줄씩 ─────────── */
export const Term: React.FC<{
  cmd: string; lines: string[]; everySec: number; badPrefix?: string; okPrefix?: string;
}> = ({ cmd, lines, everySec, badPrefix, okPrefix }) => {
  const frame = useCurrentFrame(); const { fps, height } = useVideoConfig();
  const shown = Math.floor(interpolate(frame, [0.7 * fps, (0.7 + lines.length * everySec) * fps],
    [0, lines.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  // 창 안에 실제로 몇 줄이 들어가는지 계산한다. 매직넘버를 두면 로그가 길어질 때 조용히 잘린다.
  const LINE = 35.5;                                   // fontSize 25 × lineHeight 1.42
  const inner = height - WIN.top - WIN.bottom - TITLE_H - PAD * 2 - CMD_H;
  const rows = Math.max(4, Math.floor(inner / LINE));
  const over = Math.max(0, shown - rows);              // 넘친 만큼 위로 밀어 올린다
  return (
    <div style={{ padding: "22px 28px", fontFamily: T.mono, transform: `translateY(${-over * LINE}px)` }}>
      <div style={{ color: T.ok, fontSize: 26, marginBottom: 14 }}>$ {cmd}</div>
      {lines.slice(0, shown).map((l, i) => {
        const bad = badPrefix && l.startsWith(badPrefix);
        const good = okPrefix && l.startsWith(okPrefix);
        return (
          <div key={i} style={{
            color: bad ? T.fail : good ? T.ok : T.muted, fontSize: 25, lineHeight: 1.42,
            whiteSpace: "pre", fontWeight: bad || good ? 700 : 400,
          }}>{l}</div>
        );
      })}
      {shown < lines.length && (
        <span style={{
          display: "inline-block", width: 12, height: 24, backgroundColor: T.accent,
          opacity: Math.floor(frame / 8) % 2 ? 0.9 : 0.15, verticalAlign: "middle",
        }} />
      )}
    </div>
  );
};

/* ─────────── 창 안: 실제 화면 캡처. 다시 그리지 않는다 ─────────── */
export const Shot: React.FC<{
  src: string; kind?: "image" | "video"; fromSec?: number; fit?: "contain" | "cover";
  /** 원본 가로/세로. 주석 상자 좌표를 창이 아니라 **이미지**에 묶기 위해 필요하다.
   *  contain 으로 넣으면 창 비율과 이미지 비율이 달라 레터박스가 생기고,
   *  창 기준 퍼센트를 쓰면 상자가 통째로 어긋난다. */
  aspect?: number;
  /** page — 웹 페이지처럼 폭을 채우고 위에서부터 보여준다(아래는 잘린다).
   *  fit  — 전체가 보이게 넣는다(기본). */
  mode?: "fit" | "page";
  boxes?: { x: number; y: number; w: number; h: number; at: number; label?: string; tone?: "bad" | "ok" }[];
}> = ({ src, kind = "image", fromSec = 0, fit = "contain", aspect, mode = "fit", boxes = [] }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{
      backgroundColor: "#0b0d11",
      alignItems: mode === "page" ? "stretch" : "center",
      justifyContent: mode === "page" ? "flex-start" : "center",
    }}>
      <div style={{
        position: "relative",
        ...(mode === "page"
          ? { width: "100%" }
          : aspect
            ? { height: "100%", aspectRatio: String(aspect), maxWidth: "100%" }
            : { width: "100%", height: "100%" }),
      }}>
      {kind === "video" ? (
        <Video src={staticFile(src)} trimBefore={Math.round(fromSec * fps)} muted
          style={{ width: "100%", height: "100%", objectFit: fit }} />
      ) : (
        <Img src={staticFile(src)}
          style={mode === "page"
            ? { width: "100%", height: "auto", display: "block" }
            : { width: "100%", height: "100%", objectFit: fit }} />
      )}
      {boxes.map((b, i) => {
        const on = ease(frame, fps, b.at, b.at + 0.35);
        const c = b.tone === "ok" ? T.ok : T.fail;
        return (
          <div key={i} style={{
            position: "absolute", left: `${b.x}%`, top: `${b.y}%`, width: `${b.w}%`, height: `${b.h}%`,
            border: `3px solid ${c}`, borderRadius: 6, opacity: on,
            boxShadow: `0 0 0 9999px rgba(7,8,11,${0.5 * on})`,
          }}>
            {b.label && (
              <div style={{
                position: "absolute", left: 0, top: -40, backgroundColor: c, color: "#0b0d11",
                fontFamily: T.sans, fontSize: 24, fontWeight: 700, padding: "5px 12px", borderRadius: 6,
                whiteSpace: "nowrap",
              }}>{b.label}</div>
            )}
          </div>
        );
      })}
      </div>
    </AbsoluteFill>
  );
};

/* ─────────── 자막: 창 밖 책상 위. 작업물은 가리지 않는다 ─────────── */
export const WorkshopCaptions: React.FC<{
  chunks: CaptionChunk[]; offsetSec: number;
  bottom?: number; fontSize?: number; maxWidth?: number; karaoke?: boolean;
}> = ({ chunks, offsetSec, bottom = WORKSHOP_CAPTION_BOTTOM, fontSize = 42, karaoke = false }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const t = frame / fps - offsetSec;
  const cur = chunks.find((c) => t >= c.start - 0.05 && t < c.end + 0.25);
  if (!cur) return null;
  const a = interpolate(t, [cur.start - 0.05, cur.start + 0.1], [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", left: WIN.left, right: WIN.right, bottom,
      display: "flex", alignItems: "center", gap: 20, opacity: a, pointerEvents: "none",
    }}>
      <div style={{ width: 4, alignSelf: "stretch", backgroundColor: T.accent, borderRadius: 2, flexShrink: 0 }} />
      <div style={{
        fontFamily: T.sans, fontSize, fontWeight: 700, color: T.text, lineHeight: 1.32,
        textAlign: "left",
      }}>
        {karaoke && cur.words
          ? cur.words.map((w, i) => (
              <span key={i} style={{ color: t >= w.s - 0.02 ? T.text : "rgba(232,232,234,0.34)" }}>
                {i ? " " : ""}{w.t}
              </span>
            ))
          : cur.text}
      </div>
    </div>
  );
};
