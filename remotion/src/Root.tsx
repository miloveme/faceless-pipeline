import { TemplateCompositions } from "./episode-template/compositions";
// 새 에피소드: src/<slug>/{slug.ts,scenes,index,compositions}.tsx 를 만들고(→ README.md) 여기에 두 줄 추가.
// 복사본은 export 이름이 같으므로 import 에서 이름을 바꿔 준다:
//   import { TemplateCompositions as E01Compositions } from "./e01/compositions";
//   ... <E01Compositions />

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <TemplateCompositions />
    </>
  );
};
