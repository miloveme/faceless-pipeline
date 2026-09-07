// 이 편의 slug 하나. **소재 경로는 여기서만 나온다** — 파일마다 손으로 고칠 자리를 두지 않는다.
// 에피소드 폴더가 E01_drama-clone-day 면 "e01" (pipeline/common.py 의 slug()).
// public/<SLUG>/ 와 같아야 한다. 복사본에서 바꿀 곳은 이 한 줄이다.
export const SLUG = "myepisode";

// public/<SLUG>/ 아래 파일을 가리킨다: asset("before.png") → "<SLUG>/before.png"
export const asset = (file: string) => `${SLUG}/${file}`;
