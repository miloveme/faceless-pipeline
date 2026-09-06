#!/usr/bin/env python3
"""트림(마지막 단어+PAD, 페이드아웃) + loudnorm -16 → audio/narration_final/<id>.wav,
씬 시각표 script/scenes_v2.json (t_start/t_end, LEAD/GAP), 단일 트랙 narration_track.wav.
꼬리 잡음이 whisper 단어 끝보다 앞에서 잘려야 하면 audio/bounds_override.json {"s10":{"last_word_end":21.84}}.
사용: 40_nar_finalize.py <EP>"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
info = jload(p["bounds"])
for k, v in info.items():
    if v.get("suggest_last_word_end") is not None:
        v["last_word_end"] = v["suggest_last_word_end"]; print("tail junk →", k, "end", v["last_word_end"], "(30단계 제안)")
if p["bounds_override"].exists():
    for k, v in jload(p["bounds_override"]).items(): info[k].update(v); print("override", k, v)
scenes = jload(p["scenes_v1"]); p["nar_final"].mkdir(parents=True, exist_ok=True)
t = 0.0; rows = []
for s in scenes["scenes"]:
    sid = s["id"]; out = p["nar_final"]/f"{sid}.wav"
    src = next((p["nar_raw"]/f"{sid}{e}" for e in (".wav", ".mp3", ".m4a") if (p["nar_raw"]/f"{sid}{e}").exists()), None)
    if src is None: die(f"내레이션 원본 없음: {sid}")
    end = min(info[sid]["last_word_end"] + PAD, info[sid]["dur"])
    # 직접 녹음본은 첫 단어 앞 여백이 길 수 있어 앞도 자른다(0.15s 여유). TTS는 first_word가 0에 가까워 영향 없음.
    start = max(0.0, info[sid]["first_word"] - 0.15)
    af = f"atrim={start:.3f}:{end:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={max(0,end-FADE):.3f}:d={FADE},loudnorm=I={NAR_LUFS}:TP=-1.5:LRA=11"
    run(["ffmpeg","-v","error","-y","-i",str(src),"-af",af,"-ar","44100","-ac","1",str(out)])
    d = dur(out); s["narration_file"] = str(out.relative_to(ep)); s["narration_dur"] = round(d,2)
    s["t_start"] = round(t,2); s["t_end"] = round(t+LEAD+d+GAP,2); rows.append((sid, info[sid]["dur"], d, s["t_start"], s["t_end"])); t = s["t_end"]
v = voice_cfg(); scenes["narration_voice"] = f"{v['engine']} ref={v['ref_file']} seed={v['seed']}"
scenes["lead"] = LEAD; scenes["gap"] = GAP; scenes["target_duration_sec"] = round(t,1)
jdump(scenes, p["scenes_v2"])
print("scene   raw  final  t_start   t_end"); [print(f"{a}  {b:5.1f}  {c:5.1f}  {d:7.2f}  {e:7.2f}") for a,b,c,d,e in rows]
print("total", round(t,1), "s =", round(t/60,2), "min")
sc = scenes["scenes"]
cmd = ["ffmpeg","-v","error","-y","-f","lavfi","-i",f"anullsrc=r=44100:cl=mono:d={t}"]; filt = []
for i, s in enumerate(sc, 1):
    ms = int((s["t_start"]+LEAD)*1000); cmd += ["-i", str(ep/s["narration_file"])]; filt.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]")
filt.append("[0:a]"+"".join(f"[d{i}]" for i in range(1,len(sc)+1))+f"amix=inputs={len(sc)+1}:normalize=0:dropout_transition=0[out]")
track = p["nar_final"]/"narration_track.wav"
run(cmd+["-filter_complex",";".join(filt),"-map","[out]","-t",str(t),str(track)])
run(["ffmpeg","-v","error","-y","-i",str(track),"-b:a","192k",str(p["nar_final"]/"narration_track_preview.mp3")])
print("track", lufs(track), "→", p["nar_final"]/"narration_track_preview.mp3")
