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

/**
 * 세로 화면에 다시 앉힌 씬을 위한 자리. 16:9 를 그대로 줄이면 훅이 안 서는 씬이 있다 —
 * 좌우로 붙은 대조 소재(1920×380)를 폭 1080 에 넣으면 높이가 214px, 화면의 11% 다.
 * 좌우를 갈라 상하로 쌓으면 45% 가 된다(미술 실측). 그런 씬은 이 자리를 통으로 쓴다.
 * 350 · 250 은 미술이 실측한 제목 자리와 자막 자리다.
 */
const TALL = { titleTop: 150, top: 350, h: 1320, capTop: 1670 };

export const makeShorts = (
  slug: string, scenes: Scene[], caps: CaptionMap, visualFor: VisualFor,
  /** 세로에 다시 앉힌 화면. 그런 씬만 돌려주고 나머지는 null — 기본은 16:9 를 줄여 놓는다 */
  shortsVisualFor?: (s: Scene) => React.ReactNode | null,
) => {
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
    const H = 1920;
    const SCALE = W / 1920;
    const H16 = 1080 * SCALE; // 607.5
    const top = 470; // 제목(200~) 아래, 하단 UI 안전영역(~1600 이후) 위
    // 한 씬이라도 세로로 다시 앉히면 제목을 위로 올린다 — 같은 쇼츠 안에서 제목이
    // 씬마다 움직이면 안 되므로 자리는 하나로 정한다
    const anyTall = shortsVisualFor !== undefined &&
      sceneIds.some((id) => { const s = scenes.find((x) => x.id === id); return s ? shortsVisualFor(s) !== null : false; });
    return (
      <AbsoluteFill style={{ backgroundColor: T.bg, wordBreak: "keep-all" }}>   {/* 상속된다 — Episode.tsx 와 같은 이유 */}
        <div style={{ position: "absolute", top: anyTall ? TALL.titleTop : 200, left: 0, width: W, textAlign: "center", fontFamily: T.sans, fontWeight: 700, fontSize: T.fsLead + 10, color: "#fff", lineHeight: 1.25, padding: "0 60px", whiteSpace: "pre-wrap" }}>
          {title}
        </div>
        {sceneIds.map((id) => {
          const s = scenes.find((x) => x.id === id);
          if (!s) return null;
          const dur = Math.round((s.t_end - s.t_start) * fps);
          const from = cursor;
          cursor += dur;
          const tall = shortsVisualFor ? shortsVisualFor(s) : null;
          return (
            <Sequence key={id} name={id} from={from} durationInFrames={dur} premountFor={fps}>
              {tall ? (
                <div style={{ position: "absolute", left: 0, top: TALL.top, width: W, height: TALL.h }}>
                  {tall}
                </div>
              ) : (
                <div style={{ position: "absolute", left: 0, top, width: 1920, height: 1080, transformOrigin: "top left", scale: String(SCALE) }}>
                  {visualFor(s)}
                </div>
              )}
              <Sequence from={Math.round(SCENE_LEAD * fps)} layout="none">
                <Audio src={staticFile(`${slug}/nar/${id}.mp3`)} />
              </Sequence>
              <div style={{ position: "absolute", left: 0, top: tall ? TALL.capTop : top + H16 + 40, width: W, height: tall ? H - TALL.capTop : 420 }}>
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
