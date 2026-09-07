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
          textShadow: "0 2px 6px rgba(0,0,0,0.6)",
        }}
      >
        {karaoke && cur.words
          ? captionRuns(cur.words).map((run, ri) => {
              const on = t >= run.words[0].s - 0.02;
              const body = run.words.map((w, i) => (
                <span key={i} style={{
                  color: run.hl
                    ? (t >= w.s - 0.02 ? "#12141a" : "rgba(18,20,26,0.45)")
                    : (t >= w.s - 0.02 ? T.capColor : "rgba(255,255,255,0.36)"),
                }}>{i ? " " : ""}{w.t}</span>
              ));
              return (
                <React.Fragment key={ri}>
                  {ri ? " " : ""}
                  {run.hl ? (
                    <span style={{
                      backgroundColor: on ? T.accent : "transparent",
                      padding: on ? "2px 10px" : 0,
                      margin: on ? "0 3px" : 0,
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
