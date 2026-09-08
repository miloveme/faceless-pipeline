import scenesJson from "./data/scenes_v2.json";
import captionsJson from "./data/captions.json";
import { makeEpisode, CaptionMap, Intro, Scene } from "../knowhow/Episode";
import { makeShorts } from "../knowhow/Shorts";
import { visualFor } from "./scenes";
import { SLUG } from "./slug";

// pipeline/55_remotion_sync.py 가 data/ 두 파일을 갱신한다. slug 는 slug.ts 한 곳에 있다.
const SCENES = scenesJson.scenes as Scene[];
const CAPS = captionsJson as CaptionMap;
// 인트로(씬 앞에 붙는 클립)는 script/intro.json 에 적으면 40 단계가 여기 데이터에 써 넣는다.
// 없으면 undefined 라 아무것도 안 붙는다. → docs/SCRIPT_FORMAT.md
const INTRO = (scenesJson as { intro?: Intro }).intro;
export const { Episode, EPISODE_FRAMES } = makeEpisode(SLUG, SCENES, CAPS, visualFor, "panel", INTRO);
export const { Shorts, shortsFrames } = makeShorts(SLUG, SCENES, CAPS, visualFor);
