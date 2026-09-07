# Remotion 화면

`src/knowhow/` 가 공용 컴포넌트, `src/<slug>/` 가 에피소드별 파일입니다.

## 공용 컴포넌트
| 파일 | 용도 |
|---|---|
| `theme.ts` | 색·글꼴·크기·여백·자막 토큰. 프리셋 3종(dark/paper/contrast) → [docs/DESIGN.md](../docs/DESIGN.md) |
| `Episode.tsx` | 에피소드 조립기(`makeEpisode`) + 원본 클립 재생기(`ClipPlayer`) |
| `Shorts.tsx` | 세로 쇼츠 조립기(`makeShorts`) |
| `Captions.tsx` | 화면 하단 자막 |
| `PromptCard.tsx` | 인용문 카드 — 하이라이트·취소선·타이핑·순차 등장 |
| `SplitCompare.tsx` | 좌우 영상 동시 재생 → 정지 → 확대 |
| `ImageCard.tsx` | 이미지 한 장 또는 두 장 비교, 켄번스 |
| `TextCard.tsx` | 규칙·공식·일반 텍스트 카드 |
| `Thumbnail.tsx` | 썸네일 스틸 |
| `WhiteboardClip.tsx` | 손그림 애니메이션 mp4를 어두운 톤 위에 얹기 |

## 새 에피소드 만들기

`E01_drama-clone-day` 라면 slug 는 `e01`, PREFIX 는 `E01` 입니다(`pipeline/common.py` 의 `slug()`).

1. `src/episode-template/` 을 `src/<slug>/` 로 복사
2. `index.tsx` 의 `SLUG = "myepisode"` → `"<slug>"`, `compositions.tsx` 의 `PREFIX = "TEMPLATE"` → `"<PREFIX>"`
   - **PREFIX 는 컴포지션 id 가 됩니다** (`<PREFIX>-Episode` 등). 템플릿은 계속 등록돼 있으므로 `TEMPLATE` 을 그대로 두면 id 가 겹칩니다
3. `scenes.tsx` 에서 씬 id 별 화면 지정 — **`"myepisode/..."` 로 된 소재 경로를 전부 `"<slug>/..."` 로** 바꿉니다. `public/<slug>/` 아래 실제 파일과 이름이 같아야 합니다(안 맞으면 렌더가 404 로 죽습니다)
4. `src/Root.tsx` 에 두 줄 추가 — 복사본은 export 이름이 템플릿과 같으므로 import 에서 바꿔 줍니다
   ```tsx
   import { TemplateCompositions as E01Compositions } from "./e01/compositions";
   //  <RemotionRoot> 안에:  <E01Compositions />
   ```
5. `pipeline/55_remotion_sync.py` 가 `src/<slug>/data/` 와 `public/<slug>/nar/` 를 채웁니다. 그 밖의 소재는 `15_clip_prep.py` 가 `public/<slug>/` 에 둡니다
6. 확인: `npx remotion compositions` 에 `<PREFIX>-Episode` 가 뜨고 `npx tsc --noEmit` 이 통과하면 등록된 것입니다

## 자막 안전영역
화면 하단 56px 부터 자막 상자가 옵니다(최대 2줄, 40px). 도식 문구·타임코드·캡션은 상단에 두세요.
