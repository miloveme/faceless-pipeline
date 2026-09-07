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

1. `src/episode-template/` 을 `src/<slug>/` 로 복사 — **템플릿은 제자리에 그대로 둡니다**(본보기이자 다음 편의 출발점)
2. **두 줄만 바꿉니다.** `slug.ts` 의 `SLUG = "myepisode"` → `"<slug>"`, `compositions.tsx` 의 `PREFIX = "TEMPLATE"` → `"<PREFIX>"`
   - **PREFIX 는 컴포지션 id 가 됩니다**(`<PREFIX>-Episode` 등). 템플릿은 계속 등록돼 있으므로 `TEMPLATE` 을 그대로 두면 id 가 겹쳐 `remotion compositions` 가 죽습니다
   - 소재 경로는 전부 `slug.ts` 의 `asset()` 을 지나므로 `SLUG` 한 줄이면 따라옵니다. **경로에 slug 를 직접 적지 마세요**
3. `scenes.tsx` 에서 씬 id 별 화면 지정 — 소재는 `asset("clip.mp4")` 처럼 **파일명만** 넘깁니다(`public/<slug>/clip.mp4` 를 가리킵니다). 실제 파일 이름과 달라지면 렌더가 404 로 죽습니다
4. `compositions.tsx` 에서 **편마다 바꿀 것**: 썸네일 소재·문구(`failSrc`/`fixSrc`/`headline`/`sub`/`badge`), 쇼츠에 쓸 씬(`sceneIds`)과 제목. 없는 씬 id 는 조용히 건너뜁니다
   - **BGM 을 넣으려면** `bgm: asset("bgm_lofi.mp3")` — 기본값 `""` 는 음악 없음입니다. 파일은 `pipeline/18_bgm_prep.sh` 가 `public/<slug>/` 에 -27 LUFS 로 만들어 둡니다
5. `src/Root.tsx` 에 두 줄 추가 — 복사본은 export 이름이 템플릿과 같으므로 import 에서 바꿔 줍니다. 아래는 slug 가 `e01` 일 때의 **예시**이니 `e01`·`E01` 을 이 편 것으로 바꾸세요
   ```tsx
   import { TemplateCompositions as E01Compositions } from "./e01/compositions";
   //  <RemotionRoot> 안에:  <E01Compositions />
   ```
6. `pipeline/55_remotion_sync.py` 가 `src/<slug>/data/` 와 `public/<slug>/nar/` 를 채웁니다. 그 밖의 소재는 `15_clip_prep.py` 가 `public/<slug>/` 에 둡니다
7. 확인 — 세 개가 다 통과해야 합니다
   ```bash
   # 소재 경로가 전부 asset() 을 지나는가 — 0줄이어야 합니다
   grep -rnE '"[^"]*/[^"]*\.(mp4|mov|webm|png|jpg|jpeg|gif|svg|webp|mp3|wav|m4a)"' src/<slug>/
   npx tsc --noEmit                   # 타입
   npx remotion compositions          # <PREFIX>-Episode 가 뜨는가. id 가 겹치면 여기서 죽습니다
   ```
   `tsc` 만으로는 id 충돌을 못 잡습니다. 세 번째 명령까지 돌리세요.
   경로를 직접 적으면 **남의 편 소재를 가리켜도 셋 다 통과합니다**(파일이 있으면 404 도 안 납니다).
   그래서 `55_remotion_sync.py` 가 같은 검사에 `slug.ts` 의 `SLUG` 가 이 편 것인지까지 더해 돌리고, 걸리면 종료코드 3 으로 멈춥니다.
   이 시점에 뜨는 길이는 **템플릿 데이터(5씬·50초)** 입니다. 6번을 돌리면 이 편의 길이로 바뀝니다.

## 자막 안전영역
화면 하단 56px 부터 자막 상자가 옵니다(최대 2줄, 40px). 도식 문구·타임코드·캡션은 상단에 두세요.
