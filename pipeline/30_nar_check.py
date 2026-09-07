#!/usr/bin/env python3
"""whisper로 내레이션 검사: 글자 오류율, 누락·반복(3자 이상 차이), 발화 시작·끝, 긴 무음.
→ nar_raw/whisper_cer.json, nar_raw/speech_bounds.json. 큰 차이가 있는 씬이 하나라도 있으면 종료코드 3.
사용: 30_nar_check.py <EP> [--ids ...] [--dir nar_raw]"""
import argparse
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default=""); ap.add_argument("--dir", default="nar_raw")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); readings = readings_for(ep); fixes = whisper_fixes_for(ep)
d = ep/"audio"/a.dir
if not p["tts_input"].exists(): die(f"읽기 전처리 결과가 없습니다: {p['tts_input']}")
if not d.is_dir(): die(f"음성 폴더가 없습니다: {d}")
ref = {x["id"]: x["text"] for x in jload(p["tts_input"])}
only = pick_ids(a.ids, set(ref))
cer = jload(d/"whisper_cer.json") if (d/"whisper_cer.json").exists() else {}
bounds = jload(d/"speech_bounds.json") if (d/"speech_bounds.json").exists() else {}
targets = [sid for sid in sorted(ref) if not only or sid in only]
bad, missing = [], []
for sid in targets:
    f = next((d/f"{sid}{e}" for e in (".wav", ".mp3", ".m4a") if (d/f"{sid}{e}").exists()), None)
    if f is None:
        missing.append(sid); print(f"MISS{sid} 음성 파일 없음: {d}/{sid}.(wav|mp3|m4a)", flush=True); continue
    r = check_scene(f, ref[sid], readings, fixes)
    src = f.suffix.lstrip(".")
    out = subprocess.run(["ffmpeg","-i",str(f),"-af","silencedetect=noise=-35dB:d=1.0","-f","null","-"],capture_output=True,text=True).stderr
    sil = list(zip([float(x) for x in re.findall(r"silence_start: ([0-9.]+)",out)],[float(x) for x in re.findall(r"silence_end: ([0-9.]+)",out)]))
    tail_junk = round(r["dur"] - r["last_word_end"], 2)
    cer[sid] = {"cer": r["cer"], "kind": r["kind"], "text": r["text"], "big": r["big"]}
    bounds[sid] = {"src": src, "dur": r["dur"], "first_word": r["first_word"], "last_word_end": r["last_word_end"], "last_words": r["last_words"], "silences": sil}
    if r["kind"] == "tail":
        bounds[sid]["suggest_last_word_end"] = r["suggest_last_word_end"]; bounds[sid]["tail_insert"] = r["tail_insert"]
    flag = {"ok": "ok  ", "tail": "TAIL", "content": "BAD "}[r["kind"]]
    extra = f"→ 꼬리 잡음, 실제 끝 {r['suggest_last_word_end']}s 제안 (40단계가 자동 적용)" if r["kind"] == "tail" else (r["big"] if r["big"] else "")
    print(f"{flag}{sid} cer {r['cer']:.3f} dur {r['dur']:.1f} speech {r['first_word']:.2f}-{r['last_word_end']:.2f} tail {tail_junk:.1f}s '{r['last_words']}' {extra}", flush=True)
    if r["kind"] == "content": bad.append(sid)
jdump(cer, d/"whisper_cer.json"); jdump(bounds, d/"speech_bounds.json")
print(f"검사 {len(targets)-len(missing)}/{len(targets)}씬 (전체 {len(ref)}씬) → {d}/whisper_cer.json")
print("BAD(재생성 대상):", ", ".join(bad) if bad else "none")
if missing: print("검사하지 못함(음성 없음):", ", ".join(missing))
sys.exit(3 if bad or missing else 0)
