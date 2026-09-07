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
    s["t_start"] = round(t,2); s["t_end"] = round(t+LEAD+d+GAP,2); rows.append((sid, info[sid]["dur"], d, s["t_start"], s["t_end"])); t = s["t_end"]
_bits = [pname] + [f"{k}={pcfg[k]}" for k in ("ref_file", "voice_id", "voice", "model", "seed") if pcfg.get(k) is not None]
scenes["narration_voice"] = " ".join(str(b) for b in _bits)
scenes["lead"] = LEAD; scenes["gap"] = GAP; scenes["target_duration_sec"] = round(t,1)
jdump(scenes, p["scenes_v2"])
print("scene   raw  final  t_start   t_end"); [print(f"{a}  {b:5.1f}  {c:5.1f}  {d:7.2f}  {e:7.2f}") for a,b,c,d,e in rows]
print(f"{len(rows)}/{len(scenes['scenes'])}씬 · total {round(t,1)}s = {round(t/60,2)}min · {pname}")
sc = scenes["scenes"]
cmd = ["ffmpeg","-v","error","-y","-f","lavfi","-i",f"anullsrc=r=44100:cl=mono:d={t}"]; filt = []
for i, s in enumerate(sc, 1):
    ms = int((s["t_start"]+LEAD)*1000); cmd += ["-i", str(ep/s["narration_file"])]; filt.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]")
filt.append("[0:a]"+"".join(f"[d{i}]" for i in range(1,len(sc)+1))+f"amix=inputs={len(sc)+1}:normalize=0:dropout_transition=0[out]")
track = p["nar_final"]/"narration_track.wav"
run(cmd+["-filter_complex",";".join(filt),"-map","[out]","-t",str(t),str(track)])
run(["ffmpeg","-v","error","-y","-i",str(track),"-b:a","192k",str(p["nar_final"]/"narration_track_preview.mp3")])
print("track", lufs(track), "→", p["nar_final"]/"narration_track_preview.mp3")
