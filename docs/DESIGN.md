# 화면 디자인 — 어디를 고치면 무엇이 바뀌나

화면은 코드로 그립니다(Remotion). 그래서 "디자인 파일"이 따로 없고, 대신 **바꾸는 자리가 층으로 나뉘어 있습니다.**
대부분의 경우 맨 위 층 하나만 건드리면 됩니다.

| 바꾸고 싶은 것 | 고칠 곳 | 난이도 |
|---|---|---|
| 색, 글꼴, 글자 크기, 여백, 자막 위치 | `remotion/src/knowhow/theme.ts` | 값 하나 |
| 어느 씬에 어떤 화면을 띄울지 | `remotion/src/<slug>/scenes.tsx` | 편마다 하는 일 |
| 카드의 배치·동작 자체 | `remotion/src/knowhow/*.tsx` | 코드 수정 |
| 이 편에만 필요한 그림 | `remotion/src/<slug>/` 에 새 컴포넌트 | 코드 작성 |

## 1층 — 테마 (대부분 여기서 끝난다)

`theme.ts` 에 프리셋 세 개가 들어 있습니다. `T` 가 어느 프리셋을 쓸지 정합니다.

```ts
export const T: Theme = {
  ...PRESETS.dark,      // dark | paper | contrast
};
```

- **dark** — 어두운 기본값. 실측 프레임과 코드 인용이 많은 채널에 맞습니다.
- **paper** — 밝은 종이 톤. 손그림·설명 위주 채널에 맞습니다.
- **contrast** — 검정 바탕에 큰 글자. 작은 화면에서 읽히는 것이 최우선일 때.

값 몇 개만 바꾸고 싶으면 뒤에 덮어씁니다.

```ts
export const T: Theme = {
  ...PRESETS.dark,
  accent: "#66d9ef",    // 강조색만 바꾸기
  fsCaption: 44,        // 자막만 키우기
  capBottom: 80,        // 자막을 조금 위로
};
```

**토큰 목록** (theme.ts 에 주석과 함께 있습니다)

| 묶음 | 토큰 |
|---|---|
| 색 | `bg` `panel` `panelLine` `text` `muted` `accent` `fail` `ok` `ruleBg` |
| 글꼴 | `sans` `mono` |
| 글자 크기 | `fsBody` `fsLead` `fsKicker` `fsLabel` `fsCaption` |
| 여백·모양 | `pad` `gap` `radius` `radiusSm` `contentW` `edge` |
| 자막 | `capBottom` `capMaxW` `capBg` `capColor` `capPad` `capRadius` |
| 움직임 | `fade` |

컴포넌트는 이 값들을 읽어서 그립니다. 그래서 `theme.ts` 한 줄을 바꾸면
모든 카드와 자막이 같이 바뀝니다 — 컴포넌트를 하나씩 고칠 필요가 없습니다.

### 글꼴 바꾸기
`theme.ts` 맨 위에서 불러옵니다. 다른 구글 폰트로 바꾸려면 import 를 갈아 끼웁니다.
한국어를 쓴다면 `subsets` 에 `korean` 이 있어야 합니다.

```ts
import { loadFont as loadSans } from "@remotion/google-fonts/Pretendard";
```

### 확인하는 법
바꾼 뒤 스튜디오에서 눈으로 봅니다.
```bash
cd remotion && npx remotion studio
```

## 2층 — 씬별 화면 선택 (편마다 하는 일)

`src/<slug>/scenes.tsx` 에서 씬 id 별로 어떤 카드를 띄울지 정합니다. 디자인이 아니라 연출입니다.

```tsx
export const visualFor: VisualFor = (s) => {
  switch (s.id) {
    case "s00": return <ClipPlayer src="myep/clip.mp4" fromSec={0} label="원본" />;
    case "s01": return <TextCard kicker="규칙" text={"..."} variant="rule" />;
    ...
  }
};
```

쓸 수 있는 카드는 [remotion/README.md](../remotion/README.md) 에 있습니다.

## 3층 — 카드 자체를 고치기

카드의 배치나 동작을 바꾸려면 `src/knowhow/` 의 해당 파일을 고칩니다.
예를 들어 좌우 비교에서 정지하는 시점이나 확대 방식은 `SplitCompare.tsx` 에 있습니다.

**여기를 고칠 때 지킬 것 하나**: 새로 쓰는 값도 토큰으로 빼세요.
숫자를 컴포넌트에 박으면 다음에 톤을 바꿀 때 또 파일을 뒤져야 합니다.

## 4층 — 이 편에만 필요한 그림

특정 편에서만 쓰는 도식은 `src/<slug>/` 안에 만듭니다. 공용 폴더에 넣지 마세요.
두 편 이상에서 쓰이게 되면 그때 `src/knowhow/` 로 올립니다.

## 안전영역

어떤 테마를 쓰든 지켜야 하는 것이 하나 있습니다.
**화면 아래 `capBottom` 부터 자막 상자가 옵니다.** 도식 문구·타임코드·캡션은 위쪽에 두세요.
아래에 두면 자막과 겹칩니다. 이건 색 문제가 아니라 배치 문제라 테마로 해결되지 않습니다.

## 처음부터 다른 디자인으로 가고 싶다면

`theme.ts` 에 프리셋을 하나 더 추가하는 것이 가장 쉽습니다.
그것으로 부족하면 `src/knowhow/` 를 복사해서 자기 컴포넌트 묶음을 만들고,
`makeEpisode` / `makeShorts` 만 그대로 쓰면 됩니다. 시각표·자막·오디오 결합은 그쪽이 담당하므로
화면만 새로 그리면 공정의 나머지는 손대지 않아도 됩니다.
