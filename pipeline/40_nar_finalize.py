#!/usr/bin/env python3
"""트림(마지막 단어+PAD, 페이드아웃) + loudnorm -16 → audio/narration_final/<id>.wav,
씬 시각표 script/scenes_v2.json (t_start/t_end, LEAD/GAP), 단일 트랙 narration_track.wav.
꼬리 잡음이 whisper 단어 끝보다 앞에서 잘려야 하면 audio/bounds_override.json {"s10":{"last_word_end":21.84}}.
사용: 40_nar_finalize.py <EP>"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
# 무거운 ffmpeg 작업 전에 설정과 입력을 먼저 검증한다 (끝에서 죽으면 한 일이 다 버려진다)
vcfg = voice_cfg(); pname = provider_name(vcfg); pcfg = provider_cfg(vcfg, pname)
for f in (p["bounds"], p["scenes_v1"]):
    if not f.exists(): die(f"입력이 없습니다: {f}")
info = jload(p["bounds"])
for k, v in info.items():
    if v.get("suggest_last_word_end") is not None:
        v["last_word_end"] = v["suggest_last_word_end"]; print("tail junk →", k, "end", v["last_word_end"], "(30단계 제안)")
if p["bounds_override"].exists():
    for k, v in jload(p["bounds_override"]).items():
        if k not in info: die(f"bounds_override 의 {k} 는 검사 결과에 없는 씬입니다: {p['bounds_override']}", 2)
        info[k].update(v); print("override", k, v)
scenes = jload(p["scenes_v1"])

# ffmpeg 를 한 번이라도 돌리기 전에 모든 씬의 입력을 확인한다
src_of = {}
no_bounds, no_audio = [], []
for s in scenes["scenes"]:
    sid = s["id"]
    if sid not in info: no_bounds.append(sid); continue
    src = next((p["nar_raw"]/f"{sid}{e}" for e in (".wav", ".mp3", ".m4a") if (p["nar_raw"]/f"{sid}{e}").exists()), None)
    if src is None: no_audio.append(sid)
    else: src_of[sid] = src
if no_bounds: die(f"검사 결과에 없는 씬: {', '.join(no_bounds)}\n  30_nar_check.py <EP> --ids {','.join(no_bounds)} 를 먼저 돌리세요.", 3)
if no_audio: die(f"내레이션 원본 없음: {', '.join(no_audio)} ({p['nar_raw']})", 3)

p["nar_final"].mkdir(parents=True, exist_ok=True)
# 내레이션이 정하지 않는 시각표 값들. **시각표 자체를 밀어서** 쓴다 — 오프셋을 아래 단계마다
# 더하게 하면 한 군데만 빠뜨려도 자막이나 챕터가 조용히 어긋난다. 시각표가 한 곳이어야 그럴 자리가 없다.
BEFORE, AFTER, MIN = timing_of(p, [s["id"] for s in scenes["scenes"]])
blocks = []          # 씬이 아닌 구간. 절대 시각으로 여기에 쌓는다
def place(sid, tbl, t):
    for it in tbl.get(sid, []):
        blocks.append({"t": round(t, 3), "sec": it["sec"], **({"clip": it["clip"]} if it.get("clip") else {})})
        t += it["sec"]
    return t
t = 0.0; rows = []
for s in scenes["scenes"]:
    sid = s["id"]; out = p["nar_final"]/f"{sid}.wav"; src = src_of[sid]
    end = min(info[sid]["last_word_end"] + PAD, info[sid]["dur"])
    # 직접 녹음본은 첫 단어 앞 여백이 길 수 있어 앞도 자른다(0.15s 여유). TTS는 first_word가 0에 가까워 영향 없음.
    start = max(0.0, info[sid]["first_word"] - 0.15)
    # 채널·샘플레이트 변환은 loudnorm **앞**에 둔다. 뒤에 두면 스테레오→모노 다운믹스(채널당 0.7071)가
    # 좌우 같은 신호에 +3.01 dB 를 리미터 뒤에 얹어 TP=-1.5 지시가 +1.5 가 된다(직접 녹음본이 스테레오일 때).
    af = (f"aformat=channel_layouts=mono,aresample=44100,atrim={start:.3f}:{end:.3f},asetpts=PTS-STARTPTS,"
          f"afade=t=out:st={max(0,end-FADE):.3f}:d={FADE},loudnorm=I={NAR_LUFS}:TP=-1.5:LRA=11")
    run(["ffmpeg","-v","error","-y","-i",str(src),"-af",af,"-ar","44100","-ac","1",str(out)])
    d = dur(out); s["narration_file"] = str(out.relative_to(ep)); s["narration_dur"] = round(d,2)
    li, lp = lufs(out)                      # 씬 음량은 여기서 확정된다. 눈으로 볼 수 있게 표에 싣는다
    lc = clipped(out)                       # 클리핑 판정은 TP 값이 아니라 풀스케일 이상 샘플 수로 본다
    t = place(sid, BEFORE, t)                              # 이 씬 앞에 끼우는 구간
    # 씬 슬롯은 내레이션이 정하지만, 화면이 더 길어야 하면 min_sec 이 하한이 된다.
    # 내레이션이 그보다 길면 내레이션이 이긴다 — 말이 잘리는 일은 없다.
    slot = max(LEAD + d + GAP, MIN.get(sid, 0.0))
    s["t_start"] = round(t,2); s["t_end"] = round(t+slot,2)
    if MIN.get(sid): s["min_sec"] = MIN[sid]
    else: s.pop("min_sec", None)
    rows.append((sid, info[sid]["dur"], d, s["t_start"], s["t_end"], li, lp, lc))
    t = place(sid, AFTER, s["t_end"])                      # 이 씬 뒤에 끼우는 구간
_bits = [pname] + [f"{k}={pcfg[k]}" for k in ("ref_file", "voice_id", "voice", "model", "seed") if pcfg.get(k) is not None]
scenes["narration_voice"] = " ".join(str(b) for b in _bits)
scenes["lead"] = LEAD; scenes["gap"] = GAP; scenes["target_duration_sec"] = round(t,1)
if blocks: scenes["blocks"] = blocks                        # 씬이 아닌 구간 (절대 시각)
else: scenes.pop("blocks", None)
scenes.pop("intro", None)                                  # 옛 이름
jdump(scenes, p["scenes_v2"])
# raw = 트림 전 원본 길이, final = 트림·정규화 뒤 내레이션 파일 길이(초). 씬 슬롯은 t_end - t_start 이고
# final 보다 여백 1.3초(앞 LEAD 0.5 + 뒤 GAP 0.8)만큼 길다 — 화면이 쓰는 것은 슬롯 쪽이다.
print("scene   raw  final  t_start   t_end     LUFS   peak  clip   (raw=트림 전, final=내레이션 파일, 슬롯=t_end-t_start)")
for a,b,c,d,e,li,lp,lc in rows:
    off = "" if li is None else ("  ←" if abs(li - NAR_LUFS) > NAR_LUFS_TOL or lc > 0 else "")
    print(f"{a}  {b:5.1f}  {c:5.1f}  {d:7.2f}  {e:7.2f}  {'    ?' if li is None else f'{li:7.1f}'}  {'    ?' if lp is None else f'{lp:5.1f}'}  {lc:4d}{off}")
_bsec = round(sum(b["sec"] for b in blocks), 2)
print(f"{len(rows)}/{len(scenes['scenes'])}씬 · total {round(t,1)}s = {round(t/60,2)}min"
      + (f" (씬 밖 구간 {len(blocks)}개 {_bsec}s 포함, 첫 씬 t_start={rows[0][3]})" if blocks else "") + f" · {pname}")
if blocks:
    print("씬 밖 구간:", " · ".join(f'{b["t"]:.2f}s {b.get("clip","(빈 화면)")} {b["sec"]}s' for b in blocks))
# 최소 길이로 늘어난 씬은 **뒤가 길어진 것**이다 — 내레이션은 t_start+LEAD 에 그대로 얹히므로
# 앞쪽 박자는 안 바뀐다. 연출이 마지막 박자 뒤에 얼마가 남는지 알아야 해서 그 값을 같이 찍는다.
_stretched = [(a, e - d, (e - d) - (LEAD + c + GAP)) for a,_,c,d,e,_,_,_ in rows
              if MIN.get(a) and e - d > LEAD + c + GAP + 0.005]
if _stretched:
    print("min_sec 으로 늘어난 씬 (슬롯 · 내레이션 끝난 뒤 남는 시간):",
          " · ".join(f"{a} {v:.2f}s (+{x:.2f}s)" for a, v, x in _stretched))
# 음량 기준은 음악 감독의 값이다(common.py). 여기서는 재서 보여만 준다 — 판정은 트랙과 마스터에서 한다
_loud = [a for a,_,_,_,_,li,_,_ in rows if li is not None and abs(li - NAR_LUFS) > NAR_LUFS_TOL]
_clip = [a for a,_,_,_,_,_,_,lc in rows if lc > 0]
print(f"음량: 목표 {NAR_LUFS} LUFS ±{NAR_LUFS_TOL} · 벗어난 씬 {len(_loud)}/{len(rows)}"
      + (f" ({', '.join(_loud)})" if _loud else "")
      + f" · 클리핑(풀스케일 이상 샘플) {len(_clip)}/{len(rows)}씬" + (f" ({', '.join(_clip)})" if _clip else ""))
print("  종료코드는 걸지 않습니다 — 편차 기준은 '균일한가'의 선이지 '멈춰야 하는가'의 선이 아닙니다(음악 감독).")
sc = scenes["scenes"]
cmd = ["ffmpeg","-v","error","-y","-f","lavfi","-i",f"anullsrc=r=44100:cl=mono:d={t}"]; filt = []
for i, s in enumerate(sc, 1):
    ms = int((s["t_start"]+LEAD)*1000); cmd += ["-i", str(ep/s["narration_file"])]; filt.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]")
filt.append("[0:a]"+"".join(f"[d{i}]" for i in range(1,len(sc)+1))+f"amix=inputs={len(sc)+1}:normalize=0:dropout_transition=0[out]")
track = p["nar_final"]/"narration_track.wav"
run(cmd+["-filter_complex",";".join(filt),"-map","[out]","-t",str(t),str(track)])
run(["ffmpeg","-v","error","-y","-i",str(track),"-b:a","192k",str(p["nar_final"]/"narration_track_preview.mp3")])
print("track", lufs(track), "→", p["nar_final"]/"narration_track_preview.mp3")
