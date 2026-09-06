import React from "react";
import { Captions } from "./Captions";
import { StageCaptions } from "./Stage";
import { WorkshopCaptions } from "./Workshop";
import { getGrammar } from "./grammar";
import type { CaptionLayer } from "./Episode";

/** 자막층 이름 → Remotion 컴포넌트. 문법이 늘면 여기 한 줄만 는다.
 *  데이터(grammar.ts)와 부품을 잇는 자리라서 따로 두었다. 한 파일에 두면 순환 참조가 난다. */
const CAPTION_LAYERS: Record<string, CaptionLayer> = {
  block: Captions,
  karaoke: StageCaptions,
  desk: WorkshopCaptions,
};

/** 자막층을 문법의 숫자(자리·크기·폭)까지 물려서 돌려준다.
 *  이 숫자가 여기서 안 넘어가면 grammars.json 은 장식일 뿐이다. */
export const captionLayerOf = (name: string): CaptionLayer => {
  const g = getGrammar(name);
  const L = CAPTION_LAYERS[g.caption.layer] as React.FC<Record<string, unknown>>;
  if (!L) throw new Error(`자막층 "${g.caption.layer}" 에 붙은 컴포넌트가 없습니다 (문법 ${name})`);
  const Bound: CaptionLayer = (props) =>
    React.createElement(L, {
      ...props,
      bottom: g.caption.bottom,
      fontSize: g.caption.size,
      maxWidth: g.caption.maxWidth,
      karaoke: g.caption.karaoke,
    });
  return Bound;
};
