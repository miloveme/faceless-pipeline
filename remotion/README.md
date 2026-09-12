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
4. `compositions.tsx` 에서 **편마다 바꿀 것**: 썸네일의 두 칸(`left`/`right`)과 문구(`headline`/`sub`/`badge`), 쇼츠에 쓸 씬(`sceneIds`)과 제목. 없는 씬 id 는 조용히 건너뜁니다
   - **썸네일 좌우가 무엇 대 무엇인지는 편이 정합니다.** 칸마다 `{src, label, color, labelColor, edgeColor, focusX, focusY, zoom}` 을 줍니다 — "실패 대 수정"인 편도 있고 "원본 대 클론"인 편도 있어서 부품이 정할 수 없습니다. **붉은/초록을 기본값처럼 쓰지 마세요**: 원본을 왼쪽에 두는 편에서 붉은 배지·붉은 윗줄은 "원본이 실패했다"로 읽힙니다
   - `color`(배지 바탕)와 `edgeColor`(칸 윗줄)는 **다른 값입니다.** 배지가 반투명 검정인 편에서 같은 값을 윗줄에 쓰면 어두운 그림 위에서 사라집니다
   - `focusX`/`focusY` 는 **잘려 나가는 쪽을 고르는 값**입니다(`objectPosition`). 소재의 비는 묻지 않습니다 — 어떤 비가 와도 칸을 채우고 넘치는 쪽만 잘립니다
   - `zoom` 은 **칸마다 따로**입니다. 맞춰야 하는 것은 배율이 아니라 **비교 대상의 크기**입니다 — 같은 순간이어도 두 소재의 프레이밍이 달라 얼굴이 몇 배씩 차이 나고, 배율을 묶으면 그 차이가 화면에 그대로 남아 큰 쪽이 "더 중요한 쪽"으로 읽힙니다. 한쪽만 확대가 덜 돼 선명하면 **"이 둘이 같은가"라는 물음에 답을 미리 알려 주기도 합니다.** `1` 이 칸을 채우는 최소 배율이고 그보다 작으면 여백이 생깁니다
   - `badge`(시리즈 배지)는 `""` 면 안 그립니다. 첫 편처럼 아직 시리즈가 없으면 비웁니다
   - **썸네일은 1280px 이 아니라 360px 로 보고 판단합니다.** 피드에서 그 크기로 보입니다. 크게 보면 안 보이고 줄이면 바로 보이는 결함이 있습니다 — 글자에 가려 한쪽 얼굴만 안 읽히는 것을 E01 에서 세 번 돌고 나서야 잡았습니다. `65_render_derived.sh` 가 `thumbs/thumb_<v>_360.png` 를 같이 뽑아 두므로 **그것부터 보세요**
   - **`split` 의 헤드라인은 한 줄 기준이고 두 칸에 걸쳐 하단에 깔립니다.** 한쪽 칸에만 얹으면 그 칸의 얼굴만 가려서, 두 칸을 같은 크기로 맞춰 놔도 **보이는 크기**가 갈립니다. 시청자가 보는 것은 얼굴이 아니라 **가려지지 않은 얼굴**입니다. 두 줄을 넣으면 블록이 아래로 넘치고 잘려도 렌더는 안 죽습니다
   - **쇼츠에서 세로로 다시 앉힐 씬이 있으면** `scenes.tsx` 에 `shortsVisualFor` 를 만들어 `makeShorts(..., shortsVisualFor)` 로 넘깁니다. 그 씬만 돌려주고 나머지는 `null` — 기본은 16:9 를 그대로 줄여 놓습니다. 좌우로 붙은 대조 소재처럼 **가로로 납작한 화면은 폭 1080 에서 높이가 200px 대로 떨어져** 훅이 서지 않습니다
   - **BGM 을 넣으려면** `bgm: asset("bgm_lofi.mp3")` — 기본값 `""` 는 음악 없음입니다. 파일은 `pipeline/18_bgm_prep.sh` 가 `public/<slug>/` 에 -27 LUFS 로 만들어 둡니다
5. **등록은 할 일이 없습니다.** `src/Root.tsx` 가 `src/e<두 자리>/compositions.tsx` 를 스스로 훑어 붙입니다 — 1번에서 폴더를 그 이름으로 만들었으면 그걸로 끝입니다. `export` 이름은 템플릿 그대로(`TemplateCompositions`) 두세요. **구별은 2번의 `PREFIX` 가 합니다**
   - **`Root.tsx` 에 편 이름을 적지 마세요.** 편 폴더는 `.gitignore` 에 있어 저장소에 안 들어가는데 `import "./e01/compositions"` 는 남습니다. 받아 간 사람은 폴더가 없으니 **빌드가 깨지고**, 적은 사람 기계에서는 폴더가 있어 `tsc` 가 통과해 안 보입니다
   - 폴더 이름이 `e<두 자리>` 가 아니면 **등록도 안 되고 `.gitignore` 도 못 걸러 편 소재가 저장소에 올라갑니다.** 둘 다 에러 없이 지나가므로 `55_remotion_sync.py` 가 슬러그 모양을 재서 종료코드 2 로 멈춥니다
6. `pipeline/55_remotion_sync.py` 가 `src/<slug>/data/` 와 `public/<slug>/nar/` 를 채웁니다. 그 밖의 소재는 `15_clip_prep.py` 가 `public/<slug>/` 에 둡니다
7. 확인 — 세 개가 다 통과해야 합니다
   ```bash
   # 소재 경로가 전부 asset() 을 지나는가 — 0줄이어야 합니다 (data/ 는 55단계가 넣는 것이라 뺍니다)
   grep -rnE '"[^"]*/[^"]*\.(mp4|mov|webm|png|jpg|jpeg|gif|svg|webp|mp3|wav|m4a)"' src/<slug>/ --exclude-dir=data
   npx tsc --noEmit                   # 타입
   npx remotion compositions          # <PREFIX>-Episode 가 뜨는가. id 가 겹치면 여기서 죽습니다
   ```
   `tsc` 만으로는 id 충돌을 못 잡습니다. 세 번째 명령까지 돌리세요.
   경로를 직접 적으면 **남의 편 소재를 가리켜도 셋 다 통과합니다**(파일이 있으면 404 도 안 납니다).
   그래서 `55_remotion_sync.py` 가 같은 검사에 `slug.ts` 의 `SLUG` 가 이 편 것인지까지 더해 돌리고, 걸리면 종료코드 3 으로 멈춥니다.
   이 시점에 뜨는 길이는 **템플릿 데이터(5씬·50초)** 입니다. 6번을 돌리면 이 편의 길이로 바뀝니다.

## 자막 안전영역
화면 하단 56px 부터 자막 상자가 옵니다(최대 2줄, 40px). 도식 문구·타임코드·캡션은 상단에 두세요.
