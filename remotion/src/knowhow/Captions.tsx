import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { T } from "./theme";

export type CaptionWord = { s: number; e: number; t: string; hl?: boolean };
// words 는 50_captions_build.py 가 넣는다. 낱말 단위로 켜는 문법(무대)이 쓴다.
export type CaptionChunk = { start: number; end: number; text: string; words?: CaptionWord[] };

/** 붙어 있는 강조 낱말을 한 덩어리로 묶는다.
 *  낱말마다 상자를 씌우면 "씬 단위" 가 상자 두 개로 쪼개져 한 구로 안 읽힌다. */
export const captionRuns = (words: CaptionWord[]) => {
  const runs: { hl: boolean; words: CaptionWord[] }[] = [];
  for (const w of words) {
    const last = runs[runs.length - 1];
    if (last && last.hl === !!w.hl) last.words.push(w);
    else runs.push({ hl: !!w.hl, words: [w] });
  }
  return runs;
};

/** 아직 안 말한 낱말의 색. **말한 낱말보다 흐리되 읽히는 선까지만 흐리다.**
 *  검수자가 「숫자와 부정어가 흐린 채로 머문다」로 잡은 자리다.
 *
 *  상자 위 0.36 → 0.62 : **실측 3.06:1 → 7.48:1** (E02 마스터 0:15.8 · 같은 프레임 대조).
 *    자막 상자(검정 0.72)는 반투명이라 뒤 화면이 밝으면 상자가 옅어지고 대비가 같이 내려간다.
 *    E02 는 어두운 편이라 107덩어리가 전부 바탕 L≤0.006 이었고, **흰 화면 위라면 4.72:1** 까지 내려간다(계산).
 *  띠 위 0.45 → 0.70 : 2.66:1 → **5.20:1**(호박 #f5b942 위 계산값). 실물에서 읽히는 것은 프레임으로 봤다.
 *
 *  더 올리면 켜지는 것이 안 보인다 — 말한 낱말은 상자 위 흰색(어두운 바탕에서 21:1), 띠 위 #12141a(10.4:1)다.
 *  **세 문법이 같은 값을 쓴다** — 펼침은 이 파일, 무대는 Stage, 작업대는 Workshop 이 여기서 가져다 쓴다. */
export const DIM_ON_BOX = "rgba(255,255,255,0.62)";
export const DIM_ON_ACCENT = "rgba(18,20,26,0.70)";

// 씬 로컬 시간 기준 자막. offsetSec = 씬 안에서 내레이션이 시작되는 시각(LEAD 0.5s)
export const Captions: React.FC<{
  chunks: CaptionChunk[];
  offsetSec: number;
  maxWidth?: number;
  fontSize?: number;
  bottom?: number;
  /** 켜지는 방식. true 면 말한 낱말만 밝다(문법이 정한다). */
  karaoke?: boolean;
}> = ({ chunks, offsetSec, maxWidth = T.capMaxW, fontSize = T.fsCaption, bottom = T.capBottom, karaoke = false }) => {
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
          wordBreak: "keep-all",   // 한글이 낱말 중간에서 끊기지 않게
          textShadow: "0 2px 6px rgba(0,0,0,0.6)",
        }}
      >
        {karaoke && cur.words
          ? captionRuns(cur.words).map((run, ri) => {
              const boxOn = run.hl && t >= run.words[0].s - 0.02;
              const body = run.words.map((w, i) => {
                const spoken = t >= w.s - 0.02;
                return (
                  <span key={i} style={{
                    color: boxOn
                      ? (spoken ? "#12141a" : DIM_ON_ACCENT)
                      : (spoken ? T.capColor : DIM_ON_BOX),
                  }}>{i ? " " : ""}{w.t}</span>
                );
              });
              return (
                <React.Fragment key={ri}>
                  {ri ? " " : ""}
                  {run.hl ? (
                    <span style={{
                      backgroundColor: boxOn ? T.accent : "transparent",
                      padding: "2px 10px",
                      margin: "0 3px",
                      borderRadius: 8,
                      boxDecorationBreak: "clone",
                      WebkitBoxDecorationBreak: "clone",
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
