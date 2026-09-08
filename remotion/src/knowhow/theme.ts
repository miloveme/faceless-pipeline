import { loadFont as loadSans } from "@remotion/google-fonts/NotoSansKR";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

/**
 * 화면의 생김새는 전부 여기서 정해진다.
 * 색·폰트뿐 아니라 글자 크기·여백·모서리·자막 위치까지 토큰이다.
 * 채널 톤을 바꾸려면 아래 PRESETS 에서 하나를 고르거나, 그 아래 THEME 에서 값을 덮어쓴다.
 * 컴포넌트 코드를 고칠 필요는 없다. → docs/DESIGN.md
 *
 * **키우는 것은 안전하고 줄이는 것은 재고 줄인다.** 통과한 값의 여유를 여기 적어 둔다 —
 * 여유를 안 적으면 다음에 줄일 때 어디가 먼저 깨지는지 아무도 모른다.
 *
 *   fsLabel 26   **여유 0.**  E01 에서 획이 가로 3.0px 로 나왔고(가는 획은 2.0px),
 *                읽히는 하한이 3px 다. **26 아래로 내려가지 마라.** s21 의 짝 숫자가 제일 먼저 깨진다.
 *   명암비 3.0   글자 밝기 ÷ 바탕 밝기(RGB 단순 평균). **E01 에서 새로 그은 선이다** —
 *                통과라 부른 것의 최저 3.20, 실패라 부른 것의 최고 1.99 사이에 그었다.
 *                사진 위에 글자를 얹으면 받침(capBg 0.72)을 깔고, 그러고도 최악 프레임에서 재라.
 *                E01 실측: 받침 0.72 로 3.20~4.79 통과 · 0.55 로 1.99~2.98 실패.
 *   s00 라벨 34  **여유 6px.**  글자가 y256 에서 끝나고 칸이 y262 부터다. 40px 이상이면 닿는다.
 */

const sans = loadSans("normal", {
  weights: ["400", "700"],
  subsets: ["korean", "latin"],
  ignoreTooManyRequestsWarning: true,
});
const mono = loadMono("normal", { weights: ["400", "700"], subsets: ["latin"] });

/**
 * mono 를 쓰는 자리에 한글이 섞여도 **정해진 얼굴**이 나오게 하는 마지막 그물.
 *
 * JetBrains Mono 에는 latin subset 만 있다. 한글 글자가 아예 없으므로 브라우저가
 * 자기 시스템에서 아무 서체나 골라 그린다. 어느 서체가 걸리느냐가 렌더하는 기계에
 * 달려 있어서, 같은 코드가 기계마다 다른 그림을 낸다.
 * 두 번째 자리에 우리가 실어 둔 sans 를 두면 latin 은 mono 가, 한글은 Noto Sans KR 이
 * 그린다. 어느 기계에서 돌려도 같은 그림이 나온다.
 *
 * 이건 faceFor 를 대신하지 않는다. faceFor 는 짧은 라벨 하나를 **한 얼굴로**
 * 통일하는 규칙이고(숫자만 mono 로 튀는 것을 막는다), 이 그물은 터미널 로그처럼
 * 면 전체가 mono 여야 하는 자리를 위한 것이다. 실제로 갈리는 자리:
 *   Term 의 로그 줄 — 세로줄이 맞아야 하므로 mono 를 못 뗀다. 한글이 섞인 줄이 있다.
 *   창 제목 — "ls -l — 산출물" 처럼 경로 + 한국어 설명이 한 줄에 온다.
 */
const MONO_STACK = `${mono.fontFamily}, ${sans.fontFamily}`;

type Theme = {
  // 색
  bg: string;          // 화면 바탕
  panel: string;       // 카드 바탕
  panelLine: string;   // 카드 테두리
  text: string;        // 본문 글자
  muted: string;       // 라벨·보조 글자
  accent: string;      // 강조 (키커, 밑줄, 하이라이트)
  fail: string;        // 실패·삭제
  ok: string;          // 성공·추가
  ruleBg: string;      // 규칙 카드의 바탕 (본문과 다르게 하고 싶을 때)

  // 글꼴
  sans: string;
  mono: string;

  // 글자 크기
  fsBody: number;      // 카드 본문
  fsLead: number;      // 큰 문장 (규칙 카드 등)
  fsKicker: number;    // 키커 (작은 윗글)
  fsLabel: number;     // 라벨·타임코드
  fsCaption: number;   // 화면 자막

  // 여백·모양
  pad: number;         // 카드 안쪽 여백
  gap: number;         // 요소 사이 간격
  radius: number;      // 카드 모서리
  radiusSm: number;    // 작은 요소 모서리
  /**
   * 테두리 굵기. **안쪽 크기를 계산하는 식에 들어가는 값이라 토큰이다.**
   * 카드 안쪽 = 상자 − 2×(lineW + pad).  이 항을 빼먹으면 한 변에 4px 이 는다 —
   * 실제로 그 4px 때문에 같은 카드를 706 과 710 으로 두 번 재고 두 번 틀렸다.
   * 값을 문서에 적지 말고 이 식으로 계산해서 쓴다(safeBottom 이 문법마다 달라
   * 안쪽 높이는 문법마다 다르다).
   */
  lineW: number;       // 카드·창 테두리
  lineWSm: number;     // 작은 요소 테두리 (칩·배지)
  contentW: number;    // 본문 최대 폭 (1920 기준)
  edge: number;        // 화면 가장자리 여백

  // 자막
  capBottom: number;   // 화면 아래에서 자막까지
  capMaxW: number;     // 자막 최대 폭
  capBg: string;       // 자막 상자 색
  capColor: string;    // 자막 글자 색
  capPad: string;      // 자막 상자 여백
  capRadius: number;

  // 움직임
  fade: number;        // 기본 페이드 초
};

export const PRESETS: Record<string, Theme> = {
  /** 어두운 기본값. 실측 프레임·코드 인용이 많은 채널에 맞는다. */
  dark: {
    bg: "#0f1115", panel: "#171a21", panelLine: "#2a2e37",
    text: "#e8e8ea", muted: "#8b8f98", accent: "#f5b942",
    fail: "#e5484d", ok: "#3ecf8e", ruleBg: "#000000",
    sans: sans.fontFamily, mono: MONO_STACK,
    fsBody: 40, fsLead: 54, fsKicker: 30, fsLabel: 26, fsCaption: 40,
    pad: 56, gap: 30, radius: 18, radiusSm: 8, lineW: 2, lineWSm: 1, contentW: 1500, edge: 40,
    capBottom: 56, capMaxW: 1500, capBg: "rgba(0,0,0,0.72)", capColor: "#ffffff",
    capPad: "10px 26px", capRadius: 10,
    fade: 0.4,
  },

  /** 밝은 종이 톤. 손그림·설명 위주 채널에 맞는다. */
  paper: {
    bg: "#f5ebd7", panel: "#fffaf0", panelLine: "#ddd0b4",
    text: "#2b2620", muted: "#7a7060", accent: "#c8641e",
    fail: "#b3261e", ok: "#2e7d4d", ruleBg: "#efe2c8",
    sans: sans.fontFamily, mono: MONO_STACK,
    fsBody: 42, fsLead: 56, fsKicker: 30, fsLabel: 26, fsCaption: 40,
    pad: 56, gap: 30, radius: 14, radiusSm: 6, lineW: 2, lineWSm: 1, contentW: 1500, edge: 44,
    capBottom: 56, capMaxW: 1500, capBg: "rgba(43,38,32,0.82)", capColor: "#fffaf0",
    capPad: "10px 26px", capRadius: 8,
    fade: 0.4,
  },

  /** 고대비. 작은 화면에서 읽히는 것을 최우선으로. */
  contrast: {
    bg: "#000000", panel: "#101010", panelLine: "#3a3a3a",
    text: "#ffffff", muted: "#a8a8a8", accent: "#ffd400",
    fail: "#ff4d4d", ok: "#3dff9a", ruleBg: "#000000",
    sans: sans.fontFamily, mono: MONO_STACK,
    fsBody: 44, fsLead: 60, fsKicker: 32, fsLabel: 28, fsCaption: 44,
    pad: 56, gap: 32, radius: 12, radiusSm: 6, lineW: 2, lineWSm: 1, contentW: 1560, edge: 40,
    capBottom: 60, capMaxW: 1560, capBg: "rgba(0,0,0,0.85)", capColor: "#ffffff",
    capPad: "12px 28px", capRadius: 8,
    fade: 0.3,
  },
};

/** 쓸 프리셋을 고른다. 개별 값만 바꾸고 싶으면 뒤에 덮어쓴다. */
export const T: Theme = {
  ...PRESETS.dark,
  // 예) accent: "#66d9ef",
  // 예) fsCaption: 44,
};

/**
 * 글자 하나에 서체를 고른다.
 *
 * 왜 필요한가 — mono(JetBrains Mono)에는 한글 글자가 없다. MONO_STACK 이 그 글자를
 * sans 로 떨어뜨려 주므로 "정해지지 않은 얼굴"은 이제 안 나오지만, 그건 그물일 뿐
 * 규칙은 아니다. 짧은 라벨 하나에 두 얼굴이 섞이면(한글은 Noto, 숫자만 JetBrains)
 * 글자 굵기와 폭이 낱말 안에서 튄다. 라벨은 통째로 한 얼굴이어야 한다.
 *
 * 그렇다고 전부 sans 로 돌리면 파일명·명령·주소가 문장처럼 보인다.
 * 그래서 글자를 보고 고른다 — 한글(또는 한자·가나)이 있으면 문장이므로 sans,
 * 없으면 mono. 손으로 고르게 두면 다음 편에서 또 틀린다.
 *
 * 쓰는 곳 — **한 덩어리로 읽히는 짧은 라벨**. 알약, 부제, 꼬리말, 배지, 코너 라벨.
 * 안 쓰는 곳 — 터미널 로그·창 제목처럼 여러 줄이 세로로 맞아야 하거나 경로가
 * 주인공인 자리. 거기서는 mono 를 유지하고 MONO_STACK 이 한글을 받는다.
 */
const NON_LATIN = /[\u1100-\u11ff\u3040-\u30ff\u3131-\u318e\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7a3\uff66-\uffdc]/;

export const faceFor = (s: unknown): string =>
  typeof s === "string" && NON_LATIN.test(s) ? T.sans : T.mono;

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
