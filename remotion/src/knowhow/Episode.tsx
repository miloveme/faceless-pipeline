import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { T, faceFor } from "./theme";
import { CaptionChunk } from "./Captions";
import { captionLayerOf } from "./captionRegistry";
import { Enter } from "./enter";
import { getGrammar } from "./grammar";

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

/**
 * **구간·씬을 가리지 않는 클립 라벨.** 「지금 보는 것이 원본인가 클론인가」를 말한다.
 * 인트로에서 뜬 것이 s00 으로 **그대로 이어져야** 해서, 두 곳이 같은 부품이어야 한다 —
 * 부품이 갈리면 이음매에서 자리나 농도가 미세하게 튀고 그게 「다시 뜬 것」으로 읽힌다.
 *
 * **상자 안에 넣지 않는다**(연출). 8.3 뒤에 두 얼굴 위로 알약이 올라앉으면
 * **증거를 그림으로 덮는다.** 그리고 상자 안에 있으면 8.3 에 받침이 빠지는 근거
 * (「T.bg 위로 내려앉으니 필요 없어진다」)가 성립하지 않아 받침을 끝까지 들고 가야 한다.
 * 자리는 (24, 214) 하나이고 x 만 칸 왼쪽 끝을 따라간다 — 규칙 하나로 끝난다.
 *
 * **받침을 안 쓴다**(사용자). 받침이 있으면 알약이 되어 「단순해 보인다」 —
 * 그림자는 **글자 가장자리만 떼어 놓아** 사진 위에서 읽히면서 상자가 안 생긴다.
 * 그래서 「사진 위에서만 받침을 켠다」는 조건 자체가 없어졌고 `bg` 인자도 없앴다.
 *
 * 2.94 에 바뀌는 것은 **크기뿐이다**. 받침·여백·모서리·색은 인트로부터 끝까지 같다(연출).
 */
/**
 * **영상 위에 얹는 글자의 테두리.** 받침 상자 대신 쓴다.
 *
 * 사용자가 「글자에 바탕이 있는 것이 별루」라고 했고, 받침을 빼면 흰 글자 대비가 **1.03** 까지
 * 떨어진다(미술 실측 · 얼린 클론 프레임 (24,214)). 그림자는 **글자 가장자리만 떼어 놓아**
 * 사진 위에서 읽히면서 상자가 안 생긴다. 인트로 클론 34장으로 재서 통과한 값이다.
 *
 * **여기 한 곳에만 있다.** 일곱 자리가 이 값을 부른다 — 값이 흩어지면 한 곳을 흔들 때
 * 나머지가 조용히 남는다. 실제로 `Corner` 만 0.72 로 고치고 **`rgba(0,0,0,0.55)` 가 네 곳에
 * 남아 있었다** — 그 0.55 는 미술이 **1.99~2.98 로 실패라고 이미 잰 값**이다(`theme.ts:19`).
 *
 * **미술 것이라 여기가 제 자리가 아닐 수 있다** — 토큰으로 옮기고 싶으면 `theme.ts` 에 넣어 주시면
 * 그쪽을 보게 바꾸겠다(엔지니어).
 *
 * **재는 법**(미술) — 획 = 정확히 그 색인 화소 · **획 둘레 각 점에서 바깥 3px 안의 최솟값**,
 * 그 분포의 **중앙값**. 「띠에서 최댓값」이 아니다 — 최댓값은 **획 자신의 안티에일리어스 껍질**을
 * 집어 대비가 늘 1.00 근처로 나온다. 그 정의는 **받침을 보고 쓴 것**이라(받침은 바탕을 한 색으로
 * 덮어 최댓값=중앙값) 그림자에 옮기면서 같이 틀렸다.
 *
 * **문턱이 없다. 기준점을 쓴다.** 3.0 은 받침 잣대의 문턱이고 이 잣대에 옮기면
 * **읽히는 라벨(f550 · 2.48)이 떨어진다.** 그래서 「라벨 2.48 과 견준다」로 잰다 —
 * **「2.48 이 읽히니 그 위는 읽힌다」까지만 말할 수 있고 그 아래는 모른다**(미술).
 * 아래를 정하려면 **안 읽히는 판본**이 하나 있어야 한다.
 *
 * 실측(미술 · 그림자 넣은 뒤):
 * ```
 * s04 카운터 22.55 · s12 「컷 검출 0」 12.69 · s10 인용 6.46 · s06 상단 문장 6.05
 * s06 앵글 이름 4.93 · s12 「10.04초」 3.35 · s04 요구 문장 **2.87**(제일 낮음)
 * 기준점 라벨 f550 **2.48**   →  **일곱이 전부 라벨보다 낫다**
 * 고치기 전 s12 두 줄은 **1.01 · 0.95** 였다
 * ```
 * 이 값은 `fsLabel` **26 · 굵기 700 · `T.text`** 에서 나왔고 거는 자리는 30·40·54·70·77 인데,
 * **위 실측이 그 일곱을 다 잰 것**이라 크기 물음은 닫혔다.
 */
export const INK_SHADOW = "0 3px 14px rgba(0,0,0,0.95), 0 1px 3px rgba(0,0,0,0.9)";

export const ClipLabel: React.FC<{
  text: string; size: number; x: number; y: number; color?: string;
}> = ({ text, size, x, y, color = T.text }) => (
  <div style={{ position: "absolute", left: x, top: y, padding: "8px 16px" }}>
    <span style={{
      fontFamily: faceFor(text), fontSize: size, color, fontWeight: 700,
      // **받침 대신 그림자다**(사용자가 직접 말한 것 · 연출 승인). 받침이 있으면 알약이 되어
      // 「단순해 보인다」. 그림자는 글자 가장자리만 떼어 놓아 **사진 위에서 읽히면서 상자가 안 생긴다.**
      // 값은 `Stage.tsx:225` 의 것을 그대로 가져왔다 — 「상자가 있으면 끄고 없으면 켠다」의 그 값이라
      // **새로 만든 수가 아니다.** 최악 배경 240.9 에서 대비 **9.6**(받침 0.72 의 3.44 보다 세다 · 미술).
      textShadow: INK_SHADOW,
    }}>{text}</span>
  </div>
);

/**
 * **인용 출처 한 줄.** 남의 저작물을 화면에 쓴 자리에만 붙인다.
 *
 * **화면 기준 덧층이다 — 문법 상자 안에 넣으면 안 된다.** `Container` 는 안쪽이
 * `overflow: hidden` 이라 그 안에 두면 좌표가 상자 기준이 되고 아래가 **잘린다.**
 * E01 s29 에서 실제로 그랬다 — 재니 명암비 **1.00**(글자가 아예 안 그려짐)이었다.
 *
 * **자리는 자막 안전영역 위다.** `safeBottom` 을 넘겨받아 식으로 쓴다 —
 * 숫자를 여기 박으면 문법마다 다른 안전영역(218·232)에서 조용히 틀린다.
 * 26px 글자를 `H − safeBottom − 50` 에 두면 바닥까지 18px 이 남는다.
 *
 * **씬과 구간(블록) 둘 다 이걸 쓴다.** 두 곳에 따로 적으면 한쪽만 고쳐진다.
 */
export const SourceNote: React.FC<{
  text: string; safeBottom: number; at?: number;
}> = ({ text, safeBottom, at = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const o = interpolate(frame, [at * fps, (at + 0.4) * fps], [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 80, top: height - safeBottom - 50,
                    width: width - 160, fontFamily: faceFor(text), fontSize: T.fsLabel,
                    color: T.text, letterSpacing: 1, opacity: o,
                    // **사진 위에 오는 자리가 있다**(E01 s26 은 얼굴 대조가 화면을 꽉 채운다).
                    // 검은 바탕만 가정하고 `T.muted` 로 뒀더니 거기서 **명암비 1.89** 였다.
                    // `ClipLabel` 이 쓰는 그림자를 그대로 쓴다 — 받침을 두면 알약이 되고,
                    // 그림자는 글자 가장자리만 떼어 놓아 사진 위에서 읽히면서 상자가 안 생긴다.
                    // 색도 `T.muted` 대신 `T.text` 다 — theme 에 **「영상 위에 muted 를 두지 마라」**가 있다.
                    textShadow: INK_SHADOW }}>{text}</div>
    </AbsoluteFill>
  );
};

/**
 * 편의 **마지막 `sec` 초**를 검정으로 덮는다. 값은 한 곳(`FADE_OUT_SEC`)에 있다.
 * `pointerEvents: none` 이라 위에 덮여도 아래가 안 막힌다.
 */
export const FADE_OUT_SEC = 0.8;
const FinalFade: React.FC<{ totalFrames: number; sec: number }> = ({ totalFrames, sec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const o = interpolate(frame, [totalFrames - sec * fps, totalFrames - 1], [0, 1],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ backgroundColor: "#000", opacity: o, pointerEvents: "none" }} />;
};

/**
 * 구간 위에 세우는 채널 한 줄. **영상 위에 오므로 `ClipLabel` 의 그림자를 쓴다.**
 * 자리는 출처 줄과 같은 띠(자막 안전영역 위)이고 **가운데 맞춤**이다 —
 * 출처는 왼쪽 구석의 고지이고 이것은 화면이 시청자에게 건네는 마지막 말이라 자리가 갈린다.
 */
const BlockChannel: React.FC<{ text: string; safeBottom: number }> = ({ text, safeBottom }) => {
  const { width, height } = useVideoConfig();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, top: height - safeBottom - 76, width,
                    textAlign: "center" }}>
        {text.split(" ").map((part, i) => (
          <span key={part} style={{ fontFamily: faceFor(part), fontSize: 52,
                                    color: i === 0 ? T.text : T.muted,
                                    marginLeft: i ? "0.6em" : 0, textShadow: INK_SHADOW }}>{part}</span>
        ))}
      </div>
    </AbsoluteFill>
  );
};

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
  // 구간에 붙는 라벨. **사용자가 두 번 말한 것이다** — 「보고 있는 영상이 어떤 건지 알고 봐야」 한다.
  // **크기·색은 여기서 안 정한다.** 편이 통째로 준다 — 안 주면 라벨이 안 붙는다.
  // 기본값을 두면 그 수가 어느 편에서든 조용히 쓰이고, 그게 오늘 넷 샌 자리다.
  blockLabel?: { size: number; x: number; y: number;
                 of: Record<string, { text: string; color: string; source?: string; channel?: string }> },
  // 구간 클립을 **세로로 자르는 창.** 소재끼리 세로 크기가 다를 때 **하나를 다른 하나에 맞춘다**(미술).
  // E01 — 원본이 1920×**762**(방송 마스터의 비 · 우리가 만든 띠가 아니다)이고 클론이 1920×1080 이라,
  // 인트로에서 원본은 레터박스로 클론은 꽉 차게 나왔다. **연달아 보면 컷에서 그림이 커진다** —
  // 「클론이 더 크다」는 이 편이 안 하는 주장이다. 그래서 **자르는 것은 클론 쪽**이다.
  // 씬 s00 이 이미 같은 창(159~921)으로 클론을 잘라 견주고 있었다. **두 자리가 갈리면
  // 같은 두 소재가 편 안에서 다른 크기로 나온다** — 그래서 값을 한 곳에서 받는다.
  blockCrop?: Record<string, { y0: number; y1: number }>,
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
    // 자르는 창이 **컴포지션 크기**를 쓴다 — 1920·1080 을 여기 안 박는다.
    const { fps, width: WIDTH, height: HEIGHT } = useVideoConfig();
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
                {/* **여기는 `<Video>` 다.** 씬 안 클립은 `OffthreadVideo`(ffmpeg 이 프레임을 뽑음)로
                    바꿨는데, 구간은 **소리가 나가야** 해서 그대로 둔다.
                    그래서 **같은 파일이 한 편에서 두 방식으로 그려지는 자리**가 있다 —
                    `intro_clone.mp4` 가 여기서 돌고 s00 에서 얼린 한 장으로 다시 나온다.
                    차는 디코딩에서만 나고 평균 1 안팎이라 안 보인다(미술 실측 · h264 잡음 6.887 의 1/5~1/12).
                    **다만 두 자리의 수를 나란히 견줄 일이 생기면 「경로가 다르다」를 먼저 적어야 한다**(미술). */}
                {b.clip && (() => {
                  const src = staticFile(`${slug}/${b.clip}.mp4`);
                  const c = blockCrop?.[b.clip];
                  if (!c) {
                    return <Video src={src} style={{ width: "100%", height: "100%", objectFit: "contain" }} />;
                  }
                  // 자른 띠를 **세로 가운데**에 놓는다 — 원본이 `contain` 으로 앉는 자리와 같아진다.
                  // 바깥은 이 `AbsoluteFill` 의 `#000` 이라 원본의 레터박스와 같은 색이다.
                  // `objectFit: "cover"` 다 — 소재가 컴포지션과 다른 크기여도 **늘어나지 않고 잘린다.**
                  // 늘어나는 것은 조용하고 잘리는 것은 보인다. (55 단계가 크기가 같은지 먼저 본다.)
                  const h = c.y1 - c.y0;
                  return (
                    <div style={{ position: "absolute", left: 0, top: (HEIGHT - h) / 2,
                                  width: WIDTH, height: h, overflow: "hidden" }}>
                      <Video src={src} style={{ position: "absolute", left: 0, top: -c.y0,
                                                width: WIDTH, height: HEIGHT, objectFit: "cover" }} />
                    </div>
                  );
                })()}
                {b.clip && blockLabel?.of[b.clip] && (
                  <ClipLabel text={blockLabel.of[b.clip].text} size={blockLabel.size}
                             x={blockLabel.x} y={blockLabel.y} color={blockLabel.of[b.clip].color} />
                )}
                {/* 남의 저작물이 든 구간에만 붙는다. 씬 쪽과 **같은 부품**이라 자리가 안 갈린다. */}
                {b.clip && blockLabel?.of[b.clip]?.source && (
                  <SourceNote text={blockLabel.of[b.clip].source as string}
                              safeBottom={getGrammar(grammar).safeBottom} />
                )}
                {/**
                  * **끝 구간에 채널을 세운다.** 검수자가 이렇게 읽었다 —
                  * 「요약 카드에서 끝났다고 읽혔는데 카드가 사라지고 클립이 8.1초 다시 시작된다.
                  *  왼쪽 위 칩은 편 내내 **「이제 예시를 보여 드립니다」**를 뜻하던 표시다.
                  *  첫 2~3초를 「아직 한 꼭지 남았나」로 읽었다」
                  * 그리고 **마지막 8.9초에 채널도 구독도 없었다** — 유튜브 끝 화면이 얹히는 자리가 거기다.
                  * 칩은 출처(우리 출력임)를 말하니 그대로 두고, **아래에 채널을 세워 「끝이다」를 말한다.**
                  */}
                {b.clip && blockLabel?.of[b.clip]?.channel && (
                  <BlockChannel text={blockLabel.of[b.clip].channel as string}
                                safeBottom={getGrammar(grammar).safeBottom} />
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
        {/**
          * **마지막 페이드.** 편이 페이드도 검정도 없이 **한 프레임에서 딱 끊기고 있었다** —
          * 검수자가 「507초에서 다음이 있는 줄 알고 기다렸다」고 했다. 끝났다는 신호가 없으면
          * 시청자는 끊긴 줄 안다(유튜브에서 끝은 정해진 모양이 있다).
          *
          * **소리는 안 건드린다.** 음량은 `40` 단계와 마스터 검사가 잡고 있는 값이라
          * 여기서 줄이면 그 수가 거짓이 된다. 화면만 검정으로 덮는다.
          */}
        <FinalFade totalFrames={EPISODE_FRAMES} sec={FADE_OUT_SEC} />
      </AbsoluteFill>
    );
  };
  return { Episode, EPISODE_FRAMES, SCENES: scenes };
};
