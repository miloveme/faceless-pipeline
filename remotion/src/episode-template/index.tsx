import scenesJson from "./data/scenes_v2.json";
import captionsJson from "./data/captions.json";
import { makeEpisode, CaptionMap, Scene } from "../knowhow/Episode";
import { makeShorts } from "../knowhow/Shorts";
import { visualFor } from "./scenes";
import { SLUG } from "./slug";

// pipeline/55_remotion_sync.py 가 data/ 두 파일을 갱신한다. slug 는 slug.ts 한 곳에 있다.
const SCENES = scenesJson.scenes as Scene[];
const CAPS = captionsJson as CaptionMap;
export const { Episode, EPISODE_FRAMES } = makeEpisode(SLUG, SCENES, CAPS, visualFor);
export const { Shorts, shortsFrames } = makeShorts(SLUG, SCENES, CAPS, visualFor);
