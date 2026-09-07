import React from "react";
import { AbsoluteFill, Easing, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { T, EASE_OUT, faceFor } from "./theme";
import { CaptionChunk, captionRuns } from "./Captions";
import { getGrammar } from "./grammar";
import { LiveGround } from "./Stage";
import { useStreamPace } from "./pacing";

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
// 표시줄 높이는 아래로 그은 1px 선을 **포함한** 값이다. remotion 이 화면에
// * { box-sizing: border-box } 를 깔아 주기 때문이다(remotion/dist/.../default-css).
// 창이 안쪽 칸을 이 값으로 빼므로, 표시줄이 실제로 이보다 높으면 안에 든 이미지와
// 그 위 주석 상자가 그만큼 어긋난다. 실측: 창 위 테두리 96, 표시줄 아래 선 152 → 97~152 = 56.
// (index.css 를 떼고 렌더해도 같은 값이 나온다 — tailwind 가 아니라 remotion 이 보장한다.)
const TITLE_H = 56;   // 제목 표시줄
const BROWSER_H = 60; // 주소 알약이 있는 표시줄은 조금 높다
const BORDER = 1;     // 창 테두리. 안쪽 칸은 좌우·상하로 이만큼씩 좁다
const PAD = 22;       // 창 안쪽 여백. Term 의 padding 과 같은 값이어야 한다
const CMD_H = 51;     // "$ 명령" 줄 (fontSize 26 + marginBottom 14)

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
        height: BROWSER_H, flexShrink: 0, display: "flex", alignItems: "center", gap: 13,
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
  // height 는 반드시 TITLE_H 다. 56 을 손으로 적어 두면 창이 안쪽 칸을 TITLE_H 로 빼는데
  // 실제 표시줄은 다른 높이가 되어, 안에 든 이미지와 그 위 주석 상자가 그 차이만큼 어긋난다.
  return (
    <div style={{
      height: TITLE_H, flexShrink: 0, display: "flex", alignItems: "center", gap: 13,
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

/* 창 안쪽 실제 칸. 창은 자기 치수를 알지만 안에 든 것은 모른다.
 * FitFrame 이 이 값을 받아야 상자를 이미지에 정확히 묶는다. */
export const FitBoxCtx = React.createContext<{ w: number; h: number } | null>(null);

export const Win: React.FC<{
  chrome?: Chrome;
  title: string;
  children: React.ReactNode;
}> = ({ chrome = "terminal", title, children }) => {
  const frame = useCurrentFrame(); const { fps, width, height } = useVideoConfig();
  const on = ease(frame, fps, 0, 0.45);
  // 테두리를 빼야 실제 칸이 나온다. 2px 을 흘리면 안에 든 이미지가 그만큼 커져
  // 창 밖으로 밀리고, 이미지 퍼센트로 찍은 주석 상자도 같이 어긋난다.
  const inner = {
    w: width - WIN.left - WIN.right - BORDER * 2,
    h: height - WIN.top - WIN.bottom - BORDER * 2 - (chrome === "browser" ? BROWSER_H : TITLE_H),
  };
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
          border: `${BORDER}px solid ${T.panelLine}`,
          boxShadow: "0 40px 90px rgba(0,0,0,0.65)",
          opacity: on,
          transform: `translateY(${(1 - on) * 14}px)`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <TitleBar chrome={chrome} title={title} />
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <FitBoxCtx.Provider value={inner}>{children}</FitBoxCtx.Provider>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ─────────── 창 안: 실제 로그가 한 줄씩 ─────────── */
/** everySec 을 주지 않으면 씬 길이에서 뽑는다 — 로그가 씬 끝까지 흐르게.
 *  손으로 맞춰 둔 값과 대조해 보면 계산이 거의 같은 값을 낸다:
 *    s09 17줄/11.4초 손 0.42 ↔ 계산 0.44
 *    s10 20줄/10.7초 손 0.40 ↔ 계산 0.34
 *    s12  7줄/19.7초 손 1.80 ↔ 계산 2.25 */
export const Term: React.FC<{
  cmd: string; lines: string[]; everySec?: number; badPrefix?: string; okPrefix?: string;
}> = ({ cmd, lines, everySec, badPrefix, okPrefix }) => {
  const frame = useCurrentFrame(); const { fps, height } = useVideoConfig();
  const st = useStreamPace(lines.length, everySec, 0.7);
  const shown = Math.floor(interpolate(frame, [st.startSec * fps, (st.startSec + lines.length * st.everySec) * fps],
    [0, lines.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  // 창 안에 실제로 몇 줄이 들어가는지 계산한다. 매직넘버를 두면 로그가 길어질 때 조용히 잘린다.
  // 담긴 칸의 높이는 창이 FitBoxCtx 로 내려 준다 — 여기서 다시 빼면 항을 하나 흘린다.
  // (실제로 그랬다: 테두리 2px 을 안 뺀 판본이 나갔다. 창이 이미 뺀 값을 받아 쓰면 그럴 일이 없고,
  //  browser 표시줄처럼 높이가 다른 창에 넣어도 저절로 맞는다.)
  const ctx = React.useContext(FitBoxCtx);
  const LINE = 35.5;                                   // fontSize 25 × lineHeight 1.42
  const boxH = ctx?.h ?? height - WIN.top - WIN.bottom - BORDER * 2 - TITLE_H;
  const rows = Math.max(4, Math.floor((boxH - PAD * 2 - CMD_H) / LINE));
  const over = Math.max(0, shown - rows);              // 넘친 만큼 위로 밀어 올린다
  return (
    <div style={{ padding: `${PAD}px 28px`, fontFamily: T.mono, transform: `translateY(${-over * LINE}px)` }}>
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

/* ─────────── 주석 상자: "여기를 보라" ───────────
 * Shot 과 StillPanel 이 같이 쓴다. 그림자·라벨·딤을 두 벌 두면 한쪽만 고쳐진다.
 *
 * 좌표는 **이 컴포넌트를 담은 상자**의 퍼센트다. 담는 쪽이 그 상자를 이미지에
 * 딱 맞춰 줘야 한다(aspect). 창이나 여백에 맞추면 레터박스만큼 통째로 어긋난다. */
export type Box = {
  x: number; y: number; w: number; h: number; at: number; label?: string; tone?: "bad" | "ok";
  /** 이 상자만 다르게. 없으면 부모의 dim 을 쓴다. */
  dim?: number;
  /** 이 상자가 다시 꺼지는 시각(초). 없으면 씬 끝까지 켜져 있다(지금까지의 동작).
   *  왜 필요한가 — 딤은 상자마다 화면 전체에 그림자를 하나씩 더 얹는다.
   *  상자 셋이 동시에 켜져 있으면 dim 0.55 가 1−(1−0.55)³ = 0.91 이 되어
   *  먼저 켠 상자 안까지 같이 어두워진다. 렌더에서 실제로 그랬다.
   *  한 장 안에서 볼 곳을 차례로 짚는 씬(s06)은 앞 상자를 끄면서 넘어간다. */
  off?: number;
};

/** 상자가 이미지에 묶였는지 알리는 표시. 칸을 이미지 크기로 맞춘 쪽만 켠다. */
export const BoundCtx = React.createContext(false);

export const Boxes: React.FC<{ boxes: Box[]; dim?: number; fade?: number }> = ({
  boxes, dim = 0.5, fade = 0.35,
}) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const bound = React.useContext(BoundCtx);
  // 산문으로 적은 규칙은 재발한다. 칸을 손으로 잡는 컴포넌트가 또 생기면 여기서 걸린다.
  // NODE_ENV 로 감싸지 않는다 — 렌더 번들은 production 이라 그렇게 두면 스튜디오에서만 돌고
  // 정작 마스터를 뽑을 때는 아무 말도 안 한다. 그리고 경고가 아니라 던진다:
  // 안 묶인 칸에 찍은 상자는 "조금 어긋난 그림"이 아니라 틀린 그림이다. 조용히 나가면 안 된다.
  if (boxes.length > 0 && !bound) {
    throw new Error(
      "[Boxes] 칸이 이미지 크기로 안 맞춰졌다. FitFrame 안에 넣어라 — " +
      "좌표가 레터박스만큼 통째로 어긋난다. (Shot 이면 aspect 를 줘라)",
    );
  }
  return (
    <>
      {boxes.map((b, i) => {
        const inn = ease(frame, fps, b.at, b.at + fade);
        // off 를 주면 그 시각에 되꺼진다. 딤이 겹쳐 쌓이지 않게 하는 유일한 방법이다.
        const out = b.off == null ? 0 : ease(frame, fps, b.off, b.off + fade);
        const on = inn * (1 - out);
        const c = b.tone === "ok" ? T.ok : T.fail;
        const k = b.dim ?? dim;
        return (
          <div key={i} style={{
            position: "absolute", left: `${b.x}%`, top: `${b.y}%`, width: `${b.w}%`, height: `${b.h}%`,
            // 좌표는 "테두리를 포함한 사각형"이다 — remotion 이 * { box-sizing: border-box }
            // 를 깔아 주므로 3px 테두리가 % 안쪽으로 그려진다. 씬은 그 전제로 좌표를 찍는다
            // (테두리가 패널을 물지 않게 사방 3px 넓혀서).
            border: `3px solid ${c}`, borderRadius: 6, opacity: on,
            ...(k > 0 ? { boxShadow: `0 0 0 9999px rgba(7,8,11,${k * on})` } : null),
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
    </>
  );
};

/* ─────────── 상자를 이미지에 묶는 칸 ───────────
 * 여태 칸을 height:100% + aspectRatio + maxWidth:100% 로 잡았다.
 * 이건 소재가 **높이에 먼저 걸릴 때만** 맞는다. 폭에 먼저 걸리면 maxWidth 가
 * 폭만 자르고 높이는 100% 로 남아, 칸 비율이 소재 비율과 달라진다.
 * 그 안에서 objectFit:contain 이 다시 레터박스를 만들고, 칸 퍼센트로 찍은
 * 상자가 그 레터박스만큼 통째로 어긋난다.
 *   s06 speaker_drift(1720×674) — 칸 1728×722, 이미지 1728×677.1, 위아래 22.4px.
 *   상자가 24px 씩 밀려 문단 3 의 위 테두리를 물었다.
 *   s17·s18 은 우연히 높이에 먼저 걸려(레터박스 0) 안 드러났을 뿐이다.
 *
 * 고친 방법 — 칸을 픽셀로 계산해서 **그려질 이미지와 같은 크기**로 만든다.
 * 그러면 칸 = 이미지라 안에서 다시 맞출 것이 없고, 상자 퍼센트가 곧 이미지 퍼센트다.
 * 담긴 칸의 치수는 창이 FitBoxCtx 로 내려 준다. 창 밖(패널 문법)에서는 avail 로 준다.
 * 어느 쪽도 없으면 화면 전체다. 여기에 매직넘버를 적어 두면 창틀을 고칠 때 조용히 어긋난다. */
export const FitFrame: React.FC<{
  /** 원본 가로/세로 */
  aspect: number;
  /** 담긴 칸의 치수(px). 창 안이면 주지 않아도 된다 — 창이 내려 준다. */
  avail?: { w: number; h: number };
  children: React.ReactNode;
}> = ({ aspect, avail, children }) => {
  const ctx = React.useContext(FitBoxCtx);
  const { width, height } = useVideoConfig();
  const box = avail ?? ctx ?? { w: width, h: height };
  const w = Math.min(box.w, box.h * aspect);
  return (
    <BoundCtx.Provider value={true}>
      <div style={{ position: "relative", width: w, height: w / aspect, flexShrink: 0 }}>{children}</div>
    </BoundCtx.Provider>
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
  /** 상자 밖을 얼마나 어둡게 깔지. 0 이면 안 깐다. 기본 0.5.
   *  상자가 "여기만 보라"고 말하는 씬(s18 같은)에서는 기본값이 맞다.
   *  하지만 소재 자체가 전후 비교면 상자 밖에도 봐야 할 증거가 있다.
   *  s17 은 한 장에 겹친 판본과 고친 판본이 나란히 있어서, 기본값으로 깔면
   *  비교 대상인 나머지 절반이 반쯤 꺼진다. 그런 씬은 0 으로 끈다. */
  dim?: number;
  boxes?: Box[];
}> = ({ src, kind = "image", fromSec = 0, fit = "contain", aspect, mode = "fit", dim = 0.5, boxes = [] }) => {
  const { fps } = useVideoConfig();
  const media = (
    <>
      {kind === "video" ? (
        <Video src={staticFile(src)} trimBefore={Math.round(fromSec * fps)} muted
          style={{ width: "100%", height: "100%", objectFit: fit }} />
      ) : (
        <Img src={staticFile(src)}
          style={mode === "page"
            ? { width: "100%", height: "auto", display: "block" }
            : { width: "100%", height: "100%", objectFit: fit }} />
      )}
      <Boxes boxes={boxes} dim={dim} />
    </>
  );
  return (
    <AbsoluteFill style={{
      backgroundColor: "#0b0d11",
      alignItems: mode === "page" ? "stretch" : "center",
      justifyContent: mode === "page" ? "flex-start" : "center",
    }}>
      {mode === "page" ? (
        /* 페이지는 폭을 채우고 아래를 자른다. 칸 높이가 곧 이미지 높이라 상자는 이미 이미지에 묶인다. */
        <BoundCtx.Provider value={true}>
          <div style={{ position: "relative", width: "100%" }}>{media}</div>
        </BoundCtx.Provider>
      ) : aspect ? (
        <FitFrame aspect={aspect}>{media}</FitFrame>
      ) : (
        /* aspect 를 안 주면 칸이 창을 꽉 채운다 — 상자를 쓰면 어긋난다. 표시를 켜지 않는다. */
        <div style={{ position: "relative", width: "100%", height: "100%" }}>{media}</div>
      )}
    </AbsoluteFill>
  );
};

/* ─────────── 자막: 창 밖 책상 위. 작업물은 가리지 않는다 ─────────── */
export const WorkshopCaptions: React.FC<{
  chunks: CaptionChunk[]; offsetSec: number;
  bottom?: number; fontSize?: number; maxWidth?: number; karaoke?: boolean;
  // maxWidth 를 받아 놓고 안 쓰고 있었다. captionRegistry 는 grammars.json 의 값을
  // 꼬박꼬박 넘기는데 여기서 조용히 버려져, 문법 파일의 그 줄이 장식이 되어 있었다.
  // 지금 값(1728)은 창 폭과 같아 화면이 안 바뀐다 — 줄여야 비로소 듣는다.
}> = ({ chunks, offsetSec, bottom = WORKSHOP_CAPTION_BOTTOM, fontSize = 42,
        maxWidth = 1920 - WIN.left - WIN.right, karaoke = false }) => {
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
        maxWidth,
        wordBreak: "keep-all",   // 한글이 낱말 중간에서 끊기지 않게
        textAlign: "left",
      }}>
        {karaoke && cur.words
          ? captionRuns(cur.words).map((run, ri) => {
              const boxOn = run.hl && t >= run.words[0].s - 0.02;
              const body = run.words.map((w, i) => {
                const spoken = t >= w.s - 0.02;
                return (
                  <span key={i} style={{
                    color: boxOn
                      ? (spoken ? "#12141a" : "rgba(18,20,26,0.45)")
                      : (spoken ? T.text : "rgba(232,232,234,0.34)"),
                  }}>{i ? " " : ""}{w.t}</span>
                );
              });
              return (
                <React.Fragment key={ri}>
                  {ri ? " " : ""}
                  {run.hl ? (
                    <span style={{
                      backgroundColor: boxOn ? T.accent : "transparent",
                      padding: "2px 10px", margin: "0 3px", borderRadius: 8,
                    }}>{body}</span>
                  ) : body}
                </React.Fragment>
              );
            })
          : cur.text}
      </div>
    </div>
  );
};

/* ─────────── 화면 녹화 재생 ───────────
 * 48_rec_sync.py 가 만든 구간표대로 튼다. 구간마다 배속이 다르고,
 * 잘라낸 자리는 얼마를 건너뛰었는지 알려 주고, 모자란 자리는 정지 프레임으로 멈춘다.
 * 배속을 프레임마다 바꾸지 않고 구간을 Sequence 로 쪼개는 이유는,
 * 그래야 각 구간이 녹화의 어느 지점에서 시작하는지 정확히 못 박히기 때문이다. */
export type RecSeg =
  | { kind: "play"; clipFrom: number; clipTo: number; from: number; to: number; speed: number; cutSec?: number }
  | { kind: "freeze"; at: number; from: number; to: number; still: string };

export const RecPlayer: React.FC<{ clip: string; segments: RecSeg[] }> = ({ clip, segments }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0c10" }}>
      {segments.map((sg, i) => {
        const from = Math.round(sg.from * fps);
        const durF = Math.max(1, Math.round((sg.to - sg.from) * fps));
        return (
          <Sequence key={i} from={from} durationInFrames={durF} layout="none">
            {sg.kind === "play" ? (
              <>
                <Video
                  src={staticFile(clip)}
                  trimBefore={Math.round(sg.clipFrom * fps)}
                  trimAfter={Math.round(sg.clipTo * fps)}
                  playbackRate={sg.speed}
                  muted
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
                {sg.speed > 1.15 && <RecBadge text={`×${sg.speed.toFixed(1)}`} />}
                {sg.cutSec ? <RecBadge text={`${Math.round(sg.cutSec)}초 건너뜀`} second /> : null}
              </>
            ) : (
              <>
                <Img src={staticFile(sg.still)}
                  style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                <RecBadge text="멈춤" />
              </>
            )}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/** 지금 화면이 원속이 아니라는 표시. 없으면 시청자가 자기 눈을 의심한다. */
const RecBadge: React.FC<{ text: string; second?: boolean }> = ({ text, second }) => (
  <div style={{
    position: "absolute", right: 18, top: second ? 62 : 16,
    backgroundColor: "rgba(8,10,14,0.82)", border: `1px solid ${T.panelLine}`,
    borderRadius: 8, padding: "6px 12px",
    fontFamily: faceFor(text), fontSize: 22, color: T.muted, letterSpacing: 1,
  }}>{text}</div>
);
