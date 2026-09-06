import scenesJson from "./data/scenes_v2.json";
import captionsJson from "./data/captions.json";
import { makeEpisode, CaptionMap, Scene } from "../knowhow/Episode";
import { makeShorts } from "../knowhow/Shorts";
import { visualFor } from "./scenes";

// pipeline/55_remotion_sync.py 가 data/ 두 파일을 갱신한다.
// "myepisode" 를 에피소드 slug 로 바꾸세요 (public/<slug>/ 와 같아야 함).
const SLUG = "myepisode";
const SCENES = scenesJson.scenes as Scene[];
const CAPS = captionsJson as CaptionMap;
export const { Episode, EPISODE_FRAMES } = makeEpisode(SLUG, SCENES, CAPS, visualFor);
export const { Shorts, shortsFrames } = makeShorts(SLUG, SCENES, CAPS, visualFor);
