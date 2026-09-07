import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { T } from "./theme";
import { CaptionChunk } from "./Captions";
import { captionLayerOf } from "./captionRegistry";

// 채널 공용 에피소드 조립기. 에피소드는 (씬 시각표 JSON, 자막 JSON, visualFor)만 넘긴다.
export const FPS = 30;
export const SCENE_LEAD = 0.5; // 씬 시작 후 내레이션이 시작되기까지 (_pipeline/common.py LEAD와 같아야 함)

export type Scene = { id: string; t_start: number; t_end: number; narration_dur: number };
export type CaptionMap = Record<string, CaptionChunk[]>;
export type VisualFor = (s: Scene) => React.ReactNode;

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
      <div style={{ position: "absolute", right: 40, top: 34, fontFamily: T.mono, fontSize: 26, color: T.muted, backgroundColor: "rgba(0,0,0,0.55)", padding: "8px 16px", borderRadius: 8 }}>
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
) => {
  const CaptionsLayer = captionLayerOf(grammar);
  const EPISODE_FRAMES = Math.ceil(scenes[scenes.length - 1].t_end * FPS);
  const Episode: React.FC<{ bgm: string; bgmVolume: number }> = ({ bgm, bgmVolume }) => {
    const { fps } = useVideoConfig();
    return (
      <AbsoluteFill style={{ backgroundColor: T.bg }}>
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
