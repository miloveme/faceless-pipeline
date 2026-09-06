import React from "react";
import { AbsoluteFill } from "remotion";
import { T } from "../knowhow/theme";
import { ClipPlayer, VisualFor } from "../knowhow/Episode";
import { PromptCard } from "../knowhow/PromptCard";
import { SplitCompare } from "../knowhow/SplitCompare";
import { TextCard } from "../knowhow/TextCard";
import { ImageCard } from "../knowhow/ImageCard";

// 씬 id → 비주얼. 길이는 씬 시각표(data/scenes_v2.json)에서 오므로 여기서는 내용만 정한다.
// public/<slug>/ 아래의 파일을 경로로 참조한다.
export const visualFor: VisualFor = (s) => {
  switch (s.id) {
    case "s00":
      return <ClipPlayer src="myepisode/clip.mp4" fromSec={0} label="원본 · 2026-01-01" />;
    case "s01":
      return (
        <ImageCard mode="pair" src="myepisode/before.png" src2="myepisode/after.png"
          label="이전" label2="이후" caption="" kenBurns={false} arrowText="→" />
      );
    case "s02":
      return (
        <PromptCard title="인용" segments={[{ t: "여기에 원문을 넣습니다.", type: "plain" }]}
          reveal="none" revealEverySec={0} charsPerSec={40} strikeAtSec={0} fontSize={40} />
      );
    case "s03":
      return (
        <SplitCompare leftSrc="myepisode/a.mp4" rightSrc="myepisode/b.mp4"
          leftStill="myepisode/a_7.png" rightStill="myepisode/b_7.png"
          leftLabel="이전" rightLabel="이후" pauseAtSec={7}
          zoomLeft={{ x: 0.1, y: 0.1, w: 0.4, h: 0.4 }} zoomRight={{ x: 0.1, y: 0.1, w: 0.4, h: 0.4 }}
          zoomSec={1.4} clipSec={13} />
      );
    case "s04":
      return <TextCard kicker="규칙 한 줄" text={"여기에 결론을 한 줄로."} variant="rule" />;
    default:
      return <AbsoluteFill style={{ backgroundColor: T.bg }} />;
  }
};
