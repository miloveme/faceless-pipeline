import React from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";

/**
 * 선언한 aspect 가 소재의 실제 픽셀과 맞는지 렌더 중에 대조한다.
 *
 * 왜 필요한가 — aspect 는 파일에 이미 있는 값을 사람이 다시 적은 것이다.
 * 다시 적을 기회가 있는 한 또 틀린다. 실제로 `e00/workshop.tsx` 의
 * `1520/818`(실제 2346×1056, 어긋남 16.4%)이 마스터 네 판을 통과했다.
 * 틀린 aspect 는 "조금 작은 그림"이 아니다 — 칸이 소재 비율과 달라지면
 * 그 안에서 objectFit:contain 이 다시 레터박스를 만들고, 이미지 % 로 찍은
 * 주석 상자가 그 레터박스만큼 통째로 어긋난다. 가리키는 것이 없는 상자가 된다.
 *
 * 그래서 경고가 아니라 **멈춘다**. `Boxes` 의 문지기와 같은 판단이다.
 * `NODE_ENV` 로 감싸지 않는다 — 렌더 번들은 production 이라 그렇게 두면
 * 정확히 마스터를 뽑을 때만 입을 다문다.
 *
 * 멈추는 방법으로 delayRender/cancelRender 를 쓴다. 소재의 실제 크기는
 * 브라우저가 파일을 디코드해야 알 수 있어 동기적으로 못 읽는다.
 * cancelRender 는 mp4 가 만들어지기 **전에** 렌더 전체를 실패시킨다.
 */

/** 허용 오차. 이 편에서 가장 큰 칸(가로 1728)에서 1px 이 밀리는 값이 0.116% 라 0.1% 로 잘랐다. */
export const ASPECT_TOL = 0.001;

/** 같은 소재를 씬마다 다시 재지 않는다. 한 페이지에서 한 번이면 된다. */
const seen = new Set<string>();

const naturalSize = (src: string, kind: "image" | "video") =>
  new Promise<{ w: number; h: number }>((res, rej) => {
    const url = staticFile(src);
    if (kind === "video") {
      const v = document.createElement("video");
      v.preload = "metadata";
      v.onloadedmetadata = () => res({ w: v.videoWidth, h: v.videoHeight });
      v.onerror = () => rej(new Error("메타데이터를 못 읽는다"));
      v.src = url;
      return;
    }
    const im = new Image();
    im.onload = () => res({ w: im.naturalWidth, h: im.naturalHeight });
    im.onerror = () => rej(new Error("파일을 못 읽는다"));
    im.src = url;
  });

// 값을 알려주지 않는 정지는 두 번 일하게 만든다. 경로·선언값·실제·오차를 다 적는다.
// throw 하지 않고 cancelRender 만 부른다 — 여기는 promise 안이라 던지면 렌더를 죽이는 대신
// 처리되지 않은 거부로 새어 나간다. cancelRender 는 그 자체로 렌더 전체를 실패시킨다.
const stop = (who: string, src: string, aspect: number, tail: string): void => {
  cancelRender(
    new Error(
      `[${who}] aspect 가 소재와 다르다 — public/${src}\n` +
        `  선언  ${aspect.toFixed(6)}\n` +
        `  ${tail}\n` +
        `  고치는 법: 선언을 소재의 실제 픽셀(가로 / 세로)로 적는다. 허용 오차 ${(ASPECT_TOL * 100).toFixed(1)}%.`,
    ),
  );
};

/**
 * @param who   메시지에 찍을 부품 이름
 * @param src   staticFile 기준 경로
 * @param aspect 선언한 가로/세로. 없으면 아무것도 안 한다(상자도 못 쓴다)
 */
export const useAspectCheck = (
  who: string,
  src: string,
  aspect?: number,
  kind: "image" | "video" = "image",
) => {
  const key = `${who}|${src}|${aspect}`;
  const [handle] = React.useState<number | null>(() => {
    if (aspect == null || seen.has(key)) return null;
    seen.add(key);
    return delayRender(`[${who}] aspect 검사 ${src}`);
  });

  React.useEffect(() => {
    if (handle == null || aspect == null) return;
    let released = false;
    const release = () => {
      if (released) return;
      released = true;
      continueRender(handle);
    };
    naturalSize(src, kind).then(
      ({ w, h }) => {
        // 파일이 있어도 크기가 0 이면 못 읽은 것이다. 조용히 통과시키지 않는다.
        if (!w || !h) {
          stop(who, src, aspect, `실제  크기를 못 읽었다 (${w}×${h})`);
          return;
        }
        const real = w / h;
        const off = Math.abs(aspect - real) / real;
        if (off > ASPECT_TOL) {
          stop(
            who,
            src,
            aspect,
            `실제  ${real.toFixed(6)} (${w}×${h})\n  어긋남 ${(off * 100).toFixed(3)}%`,
          );
          return;
        }
        release();
      },
      (e: Error) => {
        stop(who, src, aspect, `실제  읽을 수 없다 — ${e.message}`);
      },
    );
    // 씬이 끝나 부품이 사라져도 렌더가 멈춰 있으면 안 된다.
    // 위 검사는 이 뒤에도 끝까지 돌고, 어긋나면 그때 cancelRender 가 렌더를 죽인다.
    return release;
  }, [handle, src, aspect, kind, who]);
};
