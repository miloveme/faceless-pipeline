import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { T, faceFor } from "./theme";
import { CaptionChunk } from "./Captions";
import { captionLayerOf } from "./captionRegistry";
import { Enter } from "./enter";

// 채널 공용 에피소드 조립기. 에피소드는 (씬 시각표 JSON, 자막 JSON, visualFor)만 넘긴다.
export const FPS = 30;
export const SCENE_LEAD = 0.5; // 씬 시작 후 내레이션이 시작되기까지 (_pipeline/common.py LEAD와 같아야 함)

export type Scene = { id: string; t_start: number; t_end: number; narration_dur: number };
export type CaptionMap = Record<string, CaptionChunk[]>;
export type VisualFor = (s: Scene) => React.ReactNode;

/**
 * **씬이 아닌 구간.** `script/timing.json` 의 `inserts` 를 40 단계가 절대 시각으로 풀어
 * `scenes_v2.json` 의 `blocks` 에 담는다. 씬 앞이든 씬 사이든 여기서는 차이가 없다 —
 * 40 이 이미 시각을 계산했으므로 이쪽은 "t 초에 이것"만 놓는다.
 *
 * `clip` 이 없으면 그 초만큼 **순검정**이다. 채널 바탕색이 아니다 — 이 구간은 채널을 보이는
 * 자리가 아니라 **비우는** 자리이고, 원본 클립의 레터박스가 이미 순검정이라 그 검정이 화면
 * 전체로 퍼졌다가 다시 열리는 것으로 이어진다. 바탕색은 미묘하게 밝아 다른 화면이 낀 것으로
 * 보인다(미술·연출). 있으면 **소리까지** 그대로 재생한다.
 *
 * **여기에 씬은 없다.** 그래서 자막도 없다 — 원본 대사에 우리 자막을 달지 않는다.
 * 씬 시각표는 40 단계가 이미 밀어서 써 두므로 아래 어디에도 오프셋을 더하지 않는다.
 */
export type Block = { t: number; sec: number; clip?: string };
/** 씬 사이 전환. 키는 **경계 앞에 오는 것**의 id. 시각표는 이 값으로 안 바뀐다 — 앞 것을 늘려 겹친다. */
export type Transition = { default: number; after: Record<string, number> };

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
  blocks: Block[] = [],
  transition: Transition = { default: 0, after: {} },
) => {
  // 전환 길이는 **경계 앞에 오는 것**이 갖는다. 앞 것의 자리를 그만큼 늘려 겹치고,
  // 들어오는 것이 그동안 움직인다. 시각표(t_start·t_end)는 안 건드린다.
  const holdOf = (id: string) => transition.after[id] ?? transition.default;
  // 클립 없는 구간의 이름에는 **시각이 들어간다.** 그래서 자리수를 고정해야 한다 —
  // 그냥 `${b.t}` 로 쓰면 9.0 을 JS 는 "9", 파이썬은 "9.0" 으로 적어 55 는 통과하는데
  // 화면에서는 열쇠가 안 맞아 조용히 default 로 돈다. 시각표가 소수 셋째까지라 셋으로 고정한다.
  const blankId = (t: number) => `빈화면@${t.toFixed(3)}`;
  // 들어오는 것이 움직이는 길이는 **바로 앞에 오는 것**의 값이다. 씬과 구간을 시각으로 한 줄에
  // 세워 앞뒤를 잡는다 — 구간이 씬 사이에 끼면 경계가 둘로 늘어나므로 씬만 봐서는 안 된다.
  const ORDER = [
    ...scenes.map((s) => ({ id: s.id, t: s.t_start })),
    ...blocks.map((b) => ({ id: b.clip ?? blankId(b.t), t: b.t })),
  ].sort((a, b) => a.t - b.t);
  const enterOf = (id: string) => {
    const i = ORDER.findIndex((x) => x.id === id);
    return i > 0 ? holdOf(ORDER[i - 1].id) : 0;      // 편의 첫 것은 들어올 데가 없다
  };
  const CaptionsLayer = captionLayerOf(grammar);
  // 마지막 구간이 마지막 씬 뒤에 올 수 있다 — 둘 중 늦은 쪽이 편의 끝이다.
  const lastT = Math.max(scenes[scenes.length - 1].t_end, ...blocks.map((b) => b.t + b.sec), 0);
  const EPISODE_FRAMES = Math.ceil(lastT * FPS);
  const Episode: React.FC<{ bgm: string; bgmVolume: number }> = ({ bgm, bgmVolume }) => {
    const { fps } = useVideoConfig();
    // word-break 는 상속되는 성질이라 **여기 한 번만** 걸면 그 아래 글자가 다 따라온다.
    // 컴포넌트마다 적으면 다음에 또 빠진다 — 실제로 s08 인용에서 빠져 낱말이 중간에서 쪼개졌다.
    return (
      <AbsoluteFill style={{ backgroundColor: T.bg, wordBreak: "keep-all" }}>
        {/* 구간의 경계를 **절대 시각을 프레임으로 반올림해서** 잡는다. 길이를 따로 반올림하면
            오차가 쌓여 끝이 다음 씬의 t_start 와 어긋나고 그 틈에 검은 프레임이 한 장 낀다. */}
        {blocks.map((b, i) => (
          <Sequence key={`blk${i}`} name={b.clip ? `구간:${b.clip}` : "구간:빈 화면"}
                    from={Math.round(b.t * fps)}
                    durationInFrames={Math.round((b.t + b.sec) * fps) - Math.round(b.t * fps)
                                      + Math.round(holdOf(b.clip ?? blankId(b.t)) * fps)}
                    premountFor={1 * fps}>
            <Enter sec={enterOf(b.clip ?? blankId(b.t))}>
              <AbsoluteFill style={{ backgroundColor: "#000" }}>
                {b.clip && (
                  <Video src={staticFile(`${slug}/${b.clip}.mp4`)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                )}
              </AbsoluteFill>
            </Enter>
          </Sequence>
        ))}
        {scenes.map((s) => {
          // 경계를 **절대 시각으로** 반올림한다. 길이를 반올림하면 앞 씬의 끝과 다음 씬의 시작이
          // 한 프레임 어긋나 이음매에 바탕색이 한 장 비치거나 두 씬이 한 장 겹친다.
          // E01 v2 마스터에 실제로 틈 2곳(10256·11328) 겹침 2곳이 있었다 — 33ms 라 눈에 안 걸린다.
          const from = Math.round(s.t_start * fps);
          const dur = Math.round(s.t_end * fps) - from;
          return (
            <Sequence key={s.id} name={s.id} from={from}
                      durationInFrames={dur + Math.round(holdOf(s.id) * fps)} premountFor={1 * fps}>
              <Enter sec={enterOf(s.id)}>{visualFor(s)}</Enter>
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
