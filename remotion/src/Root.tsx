import { Composition } from "remotion";
import { EpisodeCompositions } from "./episode-template/compositions";
// 새 에피소드: src/<slug>/{scenes,index,compositions}.tsx 를 만들고 여기에 한 줄 추가

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <EpisodeCompositions />
    </>
  );
};
