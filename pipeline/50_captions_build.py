#!/usr/bin/env python3
"""최종 wav에 whisper 단어 타임스탬프를 돌려 청크를 만들고(captions_whisper.json),
원문 대본 문장을 그 타이밍에 정렬해 captions.json을 만든다(문장 수 일치 시 1:1, 아니면 글자 수 비례).
자막 텍스트는 항상 원문(숫자·영문 표기 그대로)이고 whisper 받아쓰기는 타이밍에만 쓴다.
사용: 50_captions_build.py <EP> [--ids ...]"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default=""); ap.add_argument("--maxlen", type=int, default=42)
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); sc = jload(p["scenes_v2"]); only = set(a.ids.split(",")) if a.ids else None
wc = jload(p["caps_whisper"]) if p["caps_whisper"].exists() else {}
caps = jload(p["caps"]) if p["caps"].exists() else {}
def sentences(t):
    out = []
    for s in re.split(r"(?<=[\.\?!])\s+", t.strip()):
        s = s.strip()
        if not s: continue
        if len(s) > a.maxlen and "," in s:
            i = s.rfind(",", 0, len(s)//2 + 8)
            if i > 10: out += [s[:i+1].strip(), s[i+1:].strip()]; continue
        out.append(s)
    return out
for s in sc["scenes"]:
    sid = s["id"]
    if only and sid not in only: continue
    _, ws = transcribe(ep/s["narration_file"], words=True)
    chunks, cur, n = [], [], 0
    for w in ws:
        tok = w["word"].strip(); cur.append(w); n += len(tok)+1
        if n >= 38 or tok.endswith((".","?","!")):
            chunks.append({"start": round(cur[0]["start"],2), "end": round(cur[-1]["end"],2), "text": " ".join(x["word"].strip() for x in cur)}); cur, n = [], 0
    if cur: chunks.append({"start": round(cur[0]["start"],2), "end": round(cur[-1]["end"],2), "text": " ".join(x["word"].strip() for x in cur)})
    wc[sid] = chunks
    sents = sentences(s["narration"]); d = s["narration_dur"]
    if chunks and len(sents) == len(chunks):
        cc = [{"start": c["start"], "end": c["end"], "text": t} for c, t in zip(chunks, sents)]; mode = "1:1"
    else:
        t0 = chunks[0]["start"] if chunks else 0.1; t1 = chunks[-1]["end"] if chunks else d-0.3
        total = sum(len(x) for x in sents); acc = 0; cc = []
        for t in sents:
            a0 = t0+(t1-t0)*acc/total; acc += len(t); b0 = t0+(t1-t0)*acc/total
            cc.append({"start": round(a0,2), "end": round(b0,2), "text": t})
        mode = f"prop({len(sents)}s/{len(chunks)}c)"
    caps[sid] = cc; print(sid, mode, "max", max(len(c["text"]) for c in cc))
jdump(wc, p["caps_whisper"]); jdump(caps, p["caps"])
print("→", p["caps"])
