import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { T, faceFor } from "./theme";
import { CaptionChunk } from "./Captions";
import { captionLayerOf } from "./captionRegistry";

// 채널 공용 에피소드 조립기. 에피소드는 (씬 시각표 JSON, 자막 JSON, visualFor)만 넘긴다.
export const FPS = 30;
export const SCENE_LEAD = 0.5; // 씬 시작 후 내레이션이 시작되기까지 (_pipeline/common.py LEAD와 같아야 함)

export type Scene = { id: string; t_start: number; t_end: number; narration_dur: number };
export type CaptionMap = Record<string, CaptionChunk[]>;
export type VisualFor = (s: Scene) => React.ReactNode;

/**
 * 씬 앞에 붙는 인트로. `script/intro.json` 을 40 단계가 `scenes_v2.json` 에 옮겨 담는다.
 * `clip` 이 없는 항목은 검은 화면이고, 있는 항목은 **소리까지** 그대로 재생한다.
 *
 * **여기에 씬은 없다.** 그래서 자막도 없다 — 원본 대사에 우리 자막을 달지 않는다.
 * 씬 시각표는 40 단계가 이미 인트로만큼 밀어서 써 두므로 아래 어디에도 오프셋을 더하지 않는다.
 */
export type IntroItem = { sec: number; clip?: string };
export type Intro = { sec: number; items: IntroItem[] };

/** 자막을 그리는 층. grammars.json 의 caption.layer 이름이 이걸로 풀린다. */
export type CaptionLayer = React.FC<{ chunks: CaptionChunk[]; offsetSec: number }>;

/**
 * 원본 클립 재생 + 코너 라벨 (훅 씬용)
 *
 * framed — 자막 안전영역만큼 아래를 비우고 액자에 넣는다.
 *   완성본을 보여줄 때는 그 영상에도 자막이 구워져 있다.
 *   화면을 꽉 채우면 그 자막과 우리 자막이 같은 자리에서 겹쳐 둘 다 못 읽는다.
 *   액자에 넣으면 겹칠 자리가 없어진다.
 */
export const ClipPlayer: React.FC<{
  src: string; fromSec: number; label: string; framed?: boolean; safeBottom?: number;
}> = ({ src, fromSec, label, framed = false, safeBottom = 190 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = interpolate(frame, [0, 0.4 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", opacity: fade }}>
      <div
        style={
          framed
            ? { position: "absolute", left: 96, right: 96, top: 84, bottom: safeBottom,
                borderRadius: 14, overflow: "hidden", boxShadow: "0 30px 70px rgba(0,0,0,0.6)" }
            : { position: "absolute", inset: 0 }
        }
      >
        <Video src={staticFile(src)} trimBefore={Math.round(fromSec * fps)} muted
          style={{ width: "100%", height: "100%", objectFit: framed ? "contain" : "cover" }} />
      </div>
      <div style={{ position: "absolute", right: 40, top: 34, fontFamily: faceFor(label), fontSize: 26, color: T.muted, backgroundColor: "rgba(0,0,0,0.55)", padding: "8px 16px", borderRadius: 8 }}>
        {label}
      </div>
    </AbsoluteFill>
  );
};

/**
 * 에피소드 조립. 문법은 이름으로 받는다.
 * 자막층·안전영역은 문법이 정하고 편 안에서 바뀌지 않는다 — 자리가 튀면 영상이 망가진다.
 * 씬마다 갈리는 것(바탕·담기)은 visualFor 안에서 알아서 한다.
 */
export const makeEpisode = (
  slug: string,
  scenes: Scene[],
  caps: CaptionMap,
  visualFor: VisualFor,
  grammar: string = "panel",
  intro?: Intro,
) => {
  const CaptionsLayer = captionLayerOf(grammar);
  const EPISODE_FRAMES = Math.ceil(scenes[scenes.length - 1].t_end * FPS);
  // 인트로 항목의 경계를 **누적 초를 프레임으로 반올림해서** 잡는다. 항목마다 따로 반올림하면
  // 오차가 쌓여 마지막 경계가 첫 씬의 t_start 와 어긋나고, 그 틈에 검은 프레임이 한 장 낀다.
  const introCuts = (fps: number) => {
    const out: { from: number; dur: number; clip?: string }[] = [];
    let acc = 0, prev = 0;
    for (const it of intro?.items ?? []) {
      acc += it.sec;
      const end = Math.round(acc * fps);
      out.push({ from: prev, dur: end - prev, clip: it.clip });
      prev = end;
    }
    return out;
  };
  const Episode: React.FC<{ bgm: string; bgmVolume: number }> = ({ bgm, bgmVolume }) => {
    const { fps } = useVideoConfig();
    // word-break 는 상속되는 성질이라 **여기 한 번만** 걸면 그 아래 글자가 다 따라온다.
    // 컴포넌트마다 적으면 다음에 또 빠진다 — 실제로 s08 인용에서 빠져 낱말이 중간에서 쪼개졌다.
    return (
      <AbsoluteFill style={{ backgroundColor: T.bg, wordBreak: "keep-all" }}>
        {introCuts(fps).map((c, i) =>
          c.clip === undefined ? null : (
            <Sequence key={`intro${i}`} name={`intro:${c.clip}`} from={c.from} durationInFrames={c.dur} premountFor={1 * fps}>
              <AbsoluteFill style={{ backgroundColor: "#000" }}>
                <Video src={staticFile(`${slug}/${c.clip}.mp4`)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
              </AbsoluteFill>
            </Sequence>
          ),
        )}
        {scenes.map((s) => {
          const from = Math.round(s.t_start * fps);
          const dur = Math.round((s.t_end - s.t_start) * fps);
          return (
            <Sequence key={s.id} name={s.id} from={from} durationInFrames={dur} premountFor={1 * fps}>
              {visualFor(s)}
              <Sequence from={Math.round(SCENE_LEAD * fps)} layout="none">
                <Audio src={staticFile(`${slug}/nar/${s.id}.mp3`)} />
              </Sequence>
              <CaptionsLayer chunks={caps[s.id] ?? []} offsetSec={SCENE_LEAD} />
            </Sequence>
          );
        })}
        {bgm !== "" && <Audio src={staticFile(bgm)} volume={bgmVolume} loop />}
      </AbsoluteFill>
    );
  };
  return { Episode, EPISODE_FRAMES, SCENES: scenes };
};
