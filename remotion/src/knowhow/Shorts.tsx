import React from "react";
import { AbsoluteFill, Sequence, staticFile, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import { z } from "zod";
import { T } from "./theme";
import { Captions } from "./Captions";
import { CaptionMap, FPS, SCENE_LEAD, Scene, VisualFor } from "./Episode";

// 9:16 쇼츠: 16:9 씬을 1080폭으로 축소해 세로 프레임에 놓고, 위에 제목·아래에 자막.
export const ShortsSchema = z.object({
  sceneIds: z.array(z.string()), // 이 순서대로 이어 붙임
  title: z.string(),
  bgm: z.string(),
});
type Props = z.infer<typeof ShortsSchema>;

export const makeShorts = (slug: string, scenes: Scene[], caps: CaptionMap, visualFor: VisualFor) => {
  // 없는 씬 id 는 건너뛴다 — 대본이 아직 준비되지 않은 상태에서도 스튜디오가 열리도록
  const shortsFrames = (ids: string[]) =>
    Math.max(1, Math.ceil(ids.reduce((acc, id) => {
      const s = scenes.find((x) => x.id === id);
      return s ? acc + (s.t_end - s.t_start) : acc;
    }, 0) * FPS));
  const Shorts: React.FC<Props> = ({ sceneIds, title, bgm }) => {
    const { fps } = useVideoConfig();
    let cursor = 0;
    const W = 1080;
    const SCALE = W / 1920;
    const H16 = 1080 * SCALE; // 607.5
    const top = 470; // 제목(200~) 아래, 하단 UI 안전영역(~1600 이후) 위
    return (
      <AbsoluteFill style={{ backgroundColor: T.bg }}>
        <div style={{ position: "absolute", top: 200, left: 0, width: W, textAlign: "center", fontFamily: T.sans, fontWeight: 700, fontSize: T.fsLead + 10, color: "#fff", lineHeight: 1.25, padding: "0 60px", whiteSpace: "pre-wrap" }}>
          {title}
        </div>
        {sceneIds.map((id) => {
          const s = scenes.find((x) => x.id === id);
          if (!s) return null;
          const dur = Math.round((s.t_end - s.t_start) * fps);
          const from = cursor;
          cursor += dur;
          return (
            <Sequence key={id} name={id} from={from} durationInFrames={dur} premountFor={fps}>
              <div style={{ position: "absolute", left: 0, top, width: 1920, height: 1080, transformOrigin: "top left", scale: String(SCALE) }}>
                {visualFor(s)}
              </div>
              <Sequence from={Math.round(SCENE_LEAD * fps)} layout="none">
                <Audio src={staticFile(`${slug}/nar/${id}.mp3`)} />
              </Sequence>
              <div style={{ position: "absolute", left: 0, top: top + H16 + 40, width: W, height: 420 }}>
                <Captions chunks={caps[id] ?? []} offsetSec={SCENE_LEAD} maxWidth={980} fontSize={50} bottom={0} />
              </div>
            </Sequence>
          );
        })}
        {bgm !== "" && <Audio src={staticFile(bgm)} volume={1} loop />}
      </AbsoluteFill>
    );
  };
  return { Shorts, shortsFrames };
};
