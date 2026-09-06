import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { T } from "./theme";
import { Captions, CaptionChunk } from "./Captions";

// 채널 공용 에피소드 조립기. 에피소드는 (씬 시각표 JSON, 자막 JSON, visualFor)만 넘긴다.
export const FPS = 30;
export const SCENE_LEAD = 0.5; // 씬 시작 후 내레이션이 시작되기까지 (_pipeline/common.py LEAD와 같아야 함)

export type Scene = { id: string; t_start: number; t_end: number; narration_dur: number };
export type CaptionMap = Record<string, CaptionChunk[]>;
export type VisualFor = (s: Scene) => React.ReactNode;

// 원본 클립 재생 + 코너 라벨 (훅 씬용)
export const ClipPlayer: React.FC<{ src: string; fromSec: number; label: string }> = ({ src, fromSec, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = interpolate(frame, [0, T.fade * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", opacity: fade }}>
      <Video src={staticFile(src)} trimBefore={Math.round(fromSec * fps)} muted style={{ width: 1920, height: 1080, objectFit: "cover" }} />
      <div style={{ position: "absolute", right: T.edge, top: 34, fontFamily: T.mono, fontSize: T.fsLabel, color: T.muted, backgroundColor: "rgba(0,0,0,0.55)", padding: "8px 16px", borderRadius: T.radiusSm }}>
        {label}
      </div>
    </AbsoluteFill>
  );
};

export const makeEpisode = (slug: string, scenes: Scene[], caps: CaptionMap, visualFor: VisualFor) => {
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
              <Captions chunks={caps[s.id] ?? []} offsetSec={SCENE_LEAD} />
            </Sequence>
          );
        })}
        {bgm !== "" && <Audio src={staticFile(bgm)} volume={bgmVolume} loop />}
      </AbsoluteFill>
    );
  };
  return { Episode, EPISODE_FRAMES, SCENES: scenes };
};
