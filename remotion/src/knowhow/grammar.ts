import grammarsJson from "./grammars.json";

/**
 * 문법 데이터. grammars.json 을 읽어 타입을 씌우는 것까지만 한다.
 * 여기서는 Remotion 부품을 부르지 않는다 — 부품이 이 파일을 읽으므로 서로 부르면 순환이 된다.
 * 부품과 잇는 일은 captionRegistry.ts 가 맡는다. 색·글자크기는 theme.ts.
 */

export type Unit = "episode" | "scene";

export type Grammar = {
  label: string;
  for: string;
  ground: { unit: Unit; kind: string };
  contain: { unit: Unit; kind: string };
  type: { size: number; anchor: string };
  caption: {
    unit: Unit; layer: string; bottom: number;
    align: "left" | "center"; size: number; maxWidth: number; karaoke: boolean;
  };
  signature: { unit: Unit; kind: string; at: string };
  safeBottom: number;
  carries: string[];
};

const RAW = grammarsJson as unknown as Record<string, Grammar | string[]>;

export const GRAMMARS: Record<string, Grammar> = Object.fromEntries(
  Object.entries(RAW).filter(([k]) => k !== "_"),
) as Record<string, Grammar>;

export type GrammarName = keyof typeof GRAMMARS & string;

export const getGrammar = (name: string): Grammar => {
  const g = GRAMMARS[name];
  if (!g) throw new Error(`없는 문법: ${name} (있는 것: ${Object.keys(GRAMMARS).join(", ")})`);
  return g;
};

/** 씬이 쓰려는 내용 모양을 이 문법이 담을 수 있나. 담을 수 없으면 그 편에 그 문법을 쓰면 안 된다. */
export const canCarry = (name: string, shapes: string[]) => {
  const g = getGrammar(name);
  const missing = shapes.filter((s) => !g.carries.includes(s));
  return { ok: missing.length === 0, missing };
};
