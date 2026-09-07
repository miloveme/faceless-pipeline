import React from "react";
import { AbsoluteFill, CanvasImage, staticFile } from "remotion";
import { z } from "zod";
import { T, faceFor } from "./theme";

/**
 * 채널 바이블: 프레임 두 장을 좌우로 놓고 한 줄 문장을 얹는다.
 *
 * **좌우가 무엇인지는 편마다 다르다.** 여기 "실패 대 수정"을 박아 두면
 * 원본 대 클론을 비교하는 편에서 "우리가 실패했다가 고쳤다"로 읽힌다 — 뜻이 뒤집힌다.
 * 그래서 두 칸의 **라벨과 색을 편이 정한다**(`left` / `right`).
 * 붉은/초록도 그 편이 고르는 값이지 부품이 정하는 값이 아니다.
 */
const SideSchema = z.object({
  src: z.string(), // 프레임 이미지
  label: z.string(), // 칸 위 배지 글자
  color: z.string(), // 배지 바탕
  labelColor: z.string(), // 배지 글자
  edgeColor: z.string(), // 프레임 윗줄 — 배지와 **다른 값이다.** 배지 바탕이 반투명 검정이면
                         // 같은 값을 윗줄에 쓸 때 어두운 그림 위에서 사라진다(미술 실측)
  focusX: z.number(), // 0~1 잘려 나가는 쪽을 고른다 (칸 기준)
  focusY: z.number(),
  /**
   * 확대 배율. **칸마다 따로다** — 맞춰야 하는 것은 배율이 아니라 **비교 대상의 크기**다.
   * 원본과 클론은 같은 순간이어도 프레이밍이 달라 얼굴 크기가 몇 배씩 차이 난다.
   * 배율을 묶으면 그 차이가 그대로 화면에 남아 한쪽이 "더 중요한 쪽"으로 읽히고,
   * 흐린 쪽/선명한 쪽이 갈려 **"이 둘을 구별할 수 있나"라는 물음에 답을 미리 알려 준다.**
   * 1 이면 칸을 채우는 최소 배율(cover)이고 그보다 작게 두면 여백이 생긴다.
   */
  zoom: z.number(),
});

export const ThumbnailSchema = z.object({
  variant: z.enum(["split", "fail-only", "text-first"]),
  left: SideSchema,
  right: SideSchema,
  headline: z.string(), // 큰 글씨 (2줄까지, \n)
  sub: z.string(), // 작은 글씨
  badge: z.string(), // 시리즈 배지 (우상단)
});
type Props = z.infer<typeof ThumbnailSchema>;
type Side = z.infer<typeof SideSchema>;

/**
 * 칸 하나. **소재의 비를 묻지 않는다.**
 *
 * 예전에는 그림 높이를 `w * 9 / 16` 로 잡았다. 16:9 가 아닌 소재를 넣으면 세로로
 * 늘어나고(시네스코프 2.0:1·가림 크롭 2.5:1 이 그렇다), 칸보다 그림이 짧으면
 * 바닥이 비었다. `objectFit: cover` 면 어떤 비가 와도 칸을 채우고 넘치는 쪽만 잘린다.
 *
 * **잘려 나가는 쪽을 고르는 것은 `objectPosition` 이다.** `transformOrigin` 으로는 안 된다 —
 * 그건 확대할 때만 뜻이 있어서 `zoom: 1` 이면 focus 값이 통째로 무시되고 늘 가운데가 남는다.
 * 실제로 그렇게 짰다가 좌측 칸에 미술이 고른 인물 대신 가운데 등이 잡혔다.
 * 확대까지 하면 `scale` 이 겹치고, 그때 기준점도 같은 자리여야 한다.
 */
const Frame: React.FC<{ side: Side; w: number; h: number }> = ({ side, w, h }) => (
  <div
    style={{
      width: w,
      height: h,
      overflow: "hidden",
      position: "relative",
      borderTop: `10px solid ${side.edgeColor}`,
    }}
  >
    <CanvasImage
      src={staticFile(side.src)}
      style={{
        width: w,
        height: h,
        objectFit: "cover",
        objectPosition: `${side.focusX * 100}% ${side.focusY * 100}%`,
        transformOrigin: `${side.focusX * 100}% ${side.focusY * 100}%`,
        scale: String(side.zoom),
      }}
    />
  </div>
);

const Badge: React.FC<{ side: Side; left: number; top: number }> = ({ side, left, top }) => (
  <div
    style={{
      position: "absolute",
      left,
      top,
      fontFamily: faceFor(side.label),
      fontWeight: 700,
      fontSize: 30,
      color: side.labelColor,
      backgroundColor: side.color,
      padding: "6px 16px",
      borderRadius: 8,
    }}
  >
    {side.label}
  </div>
);

/** 시리즈 배지. 편 이름이 아니라 채널 코너 이름이 온다. 자리는 변형마다 다르다. */
const Series: React.FC<{ text: string; at: React.CSSProperties }> = ({ text, at }) =>
  text === "" ? null : (
    <div
      style={{
        position: "absolute",
        ...at,
        fontFamily: faceFor(text),
        fontWeight: 700,
        fontSize: 30,
        color: T.accent,
        letterSpacing: 4,
        textShadow: "0 2px 8px #000",
      }}
    >
      {text}
    </div>
  );

const Text: React.FC<{ headline: string; sub: string; align: "left" | "center"; size: number }> = ({
  headline,
  sub,
  align,
  size,
}) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: align === "center" ? "center" : "flex-start", gap: 10 }}>
    {headline.split("\n").map((l, i) => (
      <div
        key={i}
        style={{
          fontFamily: T.sans,
          fontWeight: 700,
          fontSize: size,
          lineHeight: 1.08,
          color: "#fff",
          textShadow: "0 3px 0 rgba(0,0,0,0.85), 0 0 24px rgba(0,0,0,0.8)",
          // 자막 가림막과 **같은 값**이다. 붉은 상자를 쓰면 안 된다 — 이 채널에서 T.fail 은
          // "이건 잘못됐다"는 뜻을 달고 다니고(s05 테두리·s03 취소선), 하필 좌측 칸 위에 오면
          // 배지·윗줄에서 뺀 「원본 = 실패」 연상이 헤드라인으로 돌아온다(미술).
          backgroundColor: T.capBg,
          padding: "6px 22px",
          borderRadius: 10,
        }}
      >
        {l}
      </div>
    ))}
    {sub !== "" && (
      <div style={{ fontFamily: faceFor(sub), fontWeight: 700, fontSize: size * 0.42, color: T.accent, textShadow: "0 2px 8px #000", marginTop: 6 }}>
        {sub}
      </div>
    )}
  </div>
);

/** split 헤드라인의 윗선. 미술이 360px 축소본에서 잡은 값 — 이 위로 두 얼굴이 거의 온전히 남는다. */
const HEAD_TOP = 530;

export const Thumbnail: React.FC<Props> = (p) => {
  const W = 1280;
  const H = 720;
  return (
    <AbsoluteFill style={{ backgroundColor: T.bg, width: W, height: H, overflow: "hidden", wordBreak: "keep-all" }}>
      {p.variant === "split" && (
        <>
          <div style={{ display: "flex" }}>
            <Frame side={p.left} w={W / 2} h={H} />
            <Frame side={p.right} w={W / 2} h={H} />
          </div>
          <div style={{ position: "absolute", left: W / 2 - 3, top: 0, width: 6, height: H, backgroundColor: "#fff" }} />
          <Badge side={p.left} left={26} top={22} />
          <Badge side={p.right} left={W / 2 + 26} top={22} />
          {/* 시리즈 배지는 좌우 배지가 차지한 위 두 자리를 피해 오른쪽 위 구석에 둔다 */}
          <Series text={p.badge} at={{ right: 26, top: 78 }} />
          {/**
            * 헤드라인은 **두 칸에 걸쳐 하단 한 줄**로 간다. 한쪽 칸에만 얹으면 그 칸의 얼굴만
            * 가려서, 두 칸을 같은 크기로 맞춰 놔도 **보이는 크기**가 갈린다.
            * 실제로 이 편에서 얼굴을 502 대 500 으로 맞췄는데 가려지고 남은 것이 294 대 500 이었다.
            * 시청자가 보는 것은 얼굴이 아니라 **가려지지 않은 얼굴**이다.
            *
            * `HEAD_TOP` 아래로 190px 뿐이라 **헤드라인은 한 줄 기준**이다. 두 줄을 넣으면
            * 블록이 250px 가까이 되어 아래로 넘치고, 넘친 부분은 잘려도 렌더가 안 죽는다.
            */}
          <div style={{ position: "absolute", left: 40, top: HEAD_TOP, width: W - 80 }}>
            <Text headline={p.headline} sub={p.sub} align="left" size={84} />
          </div>
        </>
      )}
      {p.variant === "fail-only" && (
        <>
          <Frame side={p.left} w={W} h={H} />
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 55%, rgba(0,0,0,0) 100%)" }} />
          <Series text={p.badge} at={{ left: 40, top: 40 }} />
          <div style={{ position: "absolute", left: 40, bottom: 60 }}>
            <Text headline={p.headline} sub={p.sub} align="left" size={96} />
          </div>
          {/* 강조 원 — 색은 그 칸의 색을 따른다 */}
          <div style={{ position: "absolute", left: W * 0.27, top: H * 0.27, width: 300, height: 300, borderRadius: "50%", border: `10px solid ${p.left.edgeColor}`, boxShadow: "0 0 40px rgba(0,0,0,0.6)" }} />
        </>
      )}
      {p.variant === "text-first" && (
        <>
          <div style={{ position: "absolute", right: 0, top: 0, width: W * 0.5, height: H, display: "flex", flexDirection: "column" }}>
            <Frame side={p.left} w={W * 0.5} h={H / 2} />
            <Frame side={p.right} w={W * 0.5} h={H / 2} />
          </div>
          <Series text={p.badge} at={{ left: 40, top: 44 }} />
          <div style={{ position: "absolute", left: 40, top: H / 2 - 120, width: W * 0.48 }}>
            <Text headline={p.headline} sub={p.sub} align="left" size={88} />
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};
