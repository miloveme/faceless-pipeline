import { loadFont as loadSans } from "@remotion/google-fonts/NotoSansKR";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

const sans = loadSans("normal", {
  weights: ["400", "700"],
  subsets: ["korean", "latin"],
  ignoreTooManyRequestsWarning: true,
});
const mono = loadMono("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

// 채널 바이블: 색·폰트는 여기서만 정의한다.
export const T = {
  bg: "#0f1115",
  panel: "#171a21",
  panelLine: "#2a2e37",
  text: "#e8e8ea",
  muted: "#8b8f98",
  accent: "#f5b942",
  fail: "#e5484d",
  ok: "#3ecf8e",
  sans: sans.fontFamily,
  mono: mono.fontFamily,
} as const;

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
