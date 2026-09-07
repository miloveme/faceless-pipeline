import { loadFont as loadSans } from "@remotion/google-fonts/NotoSansKR";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

/**
 * 화면의 생김새는 전부 여기서 정해진다.
 * 색·폰트뿐 아니라 글자 크기·여백·모서리·자막 위치까지 토큰이다.
 * 채널 톤을 바꾸려면 아래 PRESETS 에서 하나를 고르거나, 그 아래 THEME 에서 값을 덮어쓴다.
 * 컴포넌트 코드를 고칠 필요는 없다. → docs/DESIGN.md
 */

const sans = loadSans("normal", {
  weights: ["400", "700"],
  subsets: ["korean", "latin"],
  ignoreTooManyRequestsWarning: true,
});
const mono = loadMono("normal", { weights: ["400", "700"], subsets: ["latin"] });

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
    sans: sans.fontFamily, mono: mono.fontFamily,
    fsBody: 40, fsLead: 54, fsKicker: 30, fsLabel: 26, fsCaption: 40,
    pad: 56, gap: 30, radius: 18, radiusSm: 8, contentW: 1500, edge: 40,
    capBottom: 56, capMaxW: 1500, capBg: "rgba(0,0,0,0.72)", capColor: "#ffffff",
    capPad: "10px 26px", capRadius: 10,
    fade: 0.4,
  },

  /** 밝은 종이 톤. 손그림·설명 위주 채널에 맞는다. */
  paper: {
    bg: "#f5ebd7", panel: "#fffaf0", panelLine: "#ddd0b4",
    text: "#2b2620", muted: "#7a7060", accent: "#c8641e",
    fail: "#b3261e", ok: "#2e7d4d", ruleBg: "#efe2c8",
    sans: sans.fontFamily, mono: mono.fontFamily,
    fsBody: 42, fsLead: 56, fsKicker: 30, fsLabel: 26, fsCaption: 40,
    pad: 56, gap: 30, radius: 14, radiusSm: 6, contentW: 1500, edge: 44,
    capBottom: 56, capMaxW: 1500, capBg: "rgba(43,38,32,0.82)", capColor: "#fffaf0",
    capPad: "10px 26px", capRadius: 8,
    fade: 0.4,
  },

  /** 고대비. 작은 화면에서 읽히는 것을 최우선으로. */
  contrast: {
    bg: "#000000", panel: "#101010", panelLine: "#3a3a3a",
    text: "#ffffff", muted: "#a8a8a8", accent: "#ffd400",
    fail: "#ff4d4d", ok: "#3dff9a", ruleBg: "#000000",
    sans: sans.fontFamily, mono: mono.fontFamily,
    fsBody: 44, fsLead: 60, fsKicker: 32, fsLabel: 28, fsCaption: 44,
    pad: 56, gap: 32, radius: 12, radiusSm: 6, contentW: 1560, edge: 40,
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
 * 왜 필요한가 — mono(JetBrains Mono)는 subsets 에 latin 만 있다. 한글 글자가
 * 아예 없으므로 한글을 mono 로 쓰면 브라우저가 아무 대체 서체나 골라 그린다.
 * 정해 둔 얼굴이 아니라 **정해지지 않은 얼굴**이 나오고, 같은 화면 안에서
 * 본문(Noto Sans KR)과 다른 서체가 섞인다.
 *
 * 그렇다고 전부 sans 로 돌리면 파일명·명령·주소가 문장처럼 보인다.
 * 그래서 글자를 보고 고른다 — 한글이 있으면 문장이므로 sans, 없으면 mono.
 * 손으로 고르게 두면 다음 편에서 또 틀린다.
 *
 * 터미널·로그처럼 **면 전체가 코드인 곳**에는 쓰지 않는다. 거기서는 한글이
 * 섞여도 mono 가 맞다(줄이 세로로 맞아야 읽힌다).
 */
export const faceFor = (s: unknown): string =>
  typeof s === "string" && /[\u3131-\u318e\uac00-\ud7a3]/.test(s) ? T.sans : T.mono;

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
