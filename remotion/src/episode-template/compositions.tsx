import React from "react";
import { Composition, Folder, Still } from "remotion";
import { Thumbnail, ThumbnailSchema } from "../knowhow/Thumbnail";
import { ShortsSchema } from "../knowhow/Shorts";
import { Episode, EPISODE_FRAMES, Shorts, shortsFrames } from "./index";

const FPS = 30;
// 이 파일은 본보기다. PREFIX 는 어떤 에피소드와도 겹치지 않는 값이어야 한다 —
// 여기에 "E01" 같은 편 이름을 두면 그 편을 등록하는 순간 같은 id 를 둘이 주장한다.
// 복사본에서는 이 값을 에피소드 폴더명 앞부분(E01, E02, …)으로 바꾼다.
const PREFIX = "TEMPLATE";

export const TemplateCompositions: React.FC = () => (
  <>
    <Folder name={`${PREFIX}-episode`}>
      <Composition id={`${PREFIX}-Episode`} component={Episode}
        durationInFrames={EPISODE_FRAMES} fps={FPS} width={1920} height={1080}
        defaultProps={{ bgm: "", bgmVolume: 1 }} />
      <Still id={`${PREFIX}-Thumb-A`} component={Thumbnail} width={1280} height={720}
        schema={ThumbnailSchema}
        defaultProps={{ variant: "split", failSrc: "myepisode/before.png", fixSrc: "myepisode/after.png",
          headline: "제목 두 줄로\n짧게", sub: "부제", badge: "시리즈", zoom: 1.6, focusX: 0.1, focusY: 0.2 }} />
      <Composition id={`${PREFIX}-Shorts-1`} component={Shorts}
        durationInFrames={shortsFrames(["s00", "s04"])} fps={FPS} width={1080} height={1920}
        schema={ShortsSchema}
        defaultProps={{ sceneIds: ["s00", "s04"], title: "쇼츠 제목", bgm: "" }} />
    </Folder>
  </>
);
