import scenesJson from "./data/scenes_v2.json";
import captionsJson from "./data/captions.json";
import { makeEpisode, CaptionMap, Block, Scene, Transition } from "../knowhow/Episode";
import { makeShorts } from "../knowhow/Shorts";
import { visualFor } from "./scenes";
import { SLUG } from "./slug";

// pipeline/55_remotion_sync.py 가 data/ 두 파일을 갱신한다. slug 는 slug.ts 한 곳에 있다.
const SCENES = scenesJson.scenes as Scene[];
const CAPS = captionsJson as CaptionMap;
// 씬이 아닌 구간(인트로·씬 사이 클립)은 script/timing.json 에 적으면 40 단계가 여기에 써 넣는다.
// 없으면 빈 배열이라 아무것도 안 붙는다. → docs/SCRIPT_FORMAT.md
const BLOCKS = (scenesJson as { blocks?: Block[] }).blocks ?? [];
const TRANS = (scenesJson as { transition?: Transition }).transition ?? { default: 0, after: {} };
export const { Episode, EPISODE_FRAMES } = makeEpisode(SLUG, SCENES, CAPS, visualFor, "panel", BLOCKS, TRANS);
export const { Shorts, shortsFrames } = makeShorts(SLUG, SCENES, CAPS, visualFor);
