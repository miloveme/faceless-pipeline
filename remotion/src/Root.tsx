import { TemplateCompositions } from "./episode-template/compositions";

// 편별 컴포지션은 **스스로 붙는다.** `src/<slug>/compositions.tsx` 를 만들면 끝이고
// 이 파일은 새 편이 생겨도 손대지 않는다.
//
// 여기에 `import { ... } from "./e01/compositions"` 를 적으면 안 된다 —
// 편 폴더는 `.gitignore:44`(`remotion/src/e[0-9][0-9]/`)에 있어 저장소에 안 들어가는데
// 그 import 는 남는다. 받아 간 사람은 폴더가 없으니 **빌드가 TS2307 로 깨진다.**
// 실제로 그 상태로 커밋될 뻔했고, 이 기계에서는 폴더가 있어 `tsc` 가 통과해서 안 보였다.
// `require.context` 는 정적 import 가 아니라 **빌드 때 있는 것만 훑으므로**
// 편이 하나도 없는 사본에서도 통과한다.
//
// 정규식은 `.gitignore:44` 와 **같은 모양이어야 한다** — 한쪽만 넓으면
// 저장소에 안 올라가면서 등록도 안 되거나, 등록은 되면서 저장소에 올라간다.
// 두 줄이 갈리는 것은 `55_remotion_sync.py` 가 슬러그 모양을 재서 막는다.
declare const require: {
  context(
    dir: string,
    useSubdirectories: boolean,
    regExp: RegExp,
  ): {
    keys(): string[];
    (id: string): { TemplateCompositions?: React.FC };
  };
};

const eps = require.context("./", true, /^\.\/e\d\d\/compositions\.tsx$/);

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <TemplateCompositions />
      {eps
        .keys()
        .sort()
        .map((k) => {
          // 복사본은 export 이름이 템플릿과 같다(`TemplateCompositions`).
          // 이름을 바꿔 둔 편이 있으면 조용히 빠지므로 없으면 여기서 알린다.
          const Ep = eps(k).TemplateCompositions;
          if (!Ep) {
            throw new Error(
              `${k} 에 export 가 없습니다 — \`export const TemplateCompositions\` 여야 등록됩니다. ` +
                `템플릿을 복사했다면 export 이름은 그대로 두세요(구별은 compositions.tsx 안의 PREFIX 가 합니다).`,
            );
          }
          return <Ep key={k} />;
        })}
    </>
  );
};
