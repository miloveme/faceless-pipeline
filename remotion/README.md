# Remotion 화면

`src/knowhow/` 가 공용 컴포넌트, `src/<slug>/` 가 에피소드별 파일입니다.

## 공용 컴포넌트
| 파일 | 용도 |
|---|---|
| `theme.ts` | 색·폰트 토큰. 채널 톤을 여기서 바꿉니다 |
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
1. `src/episode-template/` 을 `src/<slug>/` 로 복사
2. `index.tsx` 의 `SLUG`, `compositions.tsx` 의 `PREFIX` 수정
3. `scenes.tsx` 에서 씬 id 별 화면 지정
4. `src/Root.tsx` 에 컴포지션 import 한 줄 추가
5. `pipeline/55_remotion_sync.py` 가 `data/` 를 채웁니다

## 자막 안전영역
화면 하단 56px 부터 자막 상자가 옵니다(최대 2줄, 40px). 도식 문구·타임코드·캡션은 상단에 두세요.
