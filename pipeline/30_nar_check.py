#!/usr/bin/env python3
"""whisper로 내레이션 검사: 숫자 완전일치, 글자 오류율, 누락·반복(3자 이상 차이), 발화 시작·끝, 긴 무음.
→ nar_raw/whisper_cer.json, nar_raw/speech_bounds.json. BAD 가 하나라도 있으면 종료코드 3.

BAD(content) 조건 셋: 내용 차이 · **숫자 읽기 누락** · **CER > 0.06**.
숫자 한 자리 오독은 CER 로 못 잡아서(118자에 한 글자면 0.013) 10단계가 남긴 subs 와 완전일치로 본다.
씬마다 "넣은 것 / 들린 것"을 나란히 찍는다 — 1자 오독(형용사→형형사)은 자동으로 못 잡아 사람이 읽는다.
BAD 가 나와도 재시도를 자동으로 걸지 않는다. 시드가 굴러가다 우연히 맞으면 원인이 덮인다.
사용: 30_nar_check.py <EP> [--ids ...] [--dir nar_raw] [--quiet-text]"""
import argparse
from common import *
# **안 준 것과 빈 것을 가른다.** default 를 "" 로 두면 --ids 를 안 줘도 pick_ids 가
# 「비어 있다」로 죽인다 — 네 스크립트가 다 그랬다(음악 감독이 잡았다). 기본은 None 이다.
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids"); ap.add_argument("--dir", default="nar_raw")
ap.add_argument("--quiet-text", action="store_true", help='씬마다 "넣은 것 / 들린 것"을 찍지 않는다')
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); readings = readings_for(ep); fixes = whisper_fixes_for(ep)
d = ep/"audio"/a.dir
if not p["tts_input"].exists(): die(f"읽기 전처리 결과가 없습니다: {p['tts_input']}")
if not d.is_dir(): die(f"음성 폴더가 없습니다: {d}")
_tts = jload(p["tts_input"])
# 음성이 **어느 판본으로 만들어졌나.** 아래 검사는 tts_input 과 받아쓰기를 대조하는데
# 둘 다 옛것이면 서로 맞는다 — 대본이 뒤로 움직이면 검사도 같이 움직인다.
_drift = script_drift(p, {x["id"]: x["script_sha"] for x in _tts if x.get("script_sha")})
if _drift:
    print(f"주의: 대본이 바뀐 뒤 다시 만들지 않은 씬 {len(_drift)}개 — {', '.join(_drift)}")
    print("  그 씬은 옛 문장을 읽은 음성이라 아래 CER 이 0 이어도 지금 대본과 다릅니다.")
    print(f"  다시 만들려면: 10_tts_prep.py {a.ep} --ids {','.join(_drift)} 뒤 20 · 30")
    print("  일부러 옛 음성을 쓰는 중이면 그대로 두세요 — 멈추지 않습니다.")
ref = {x["id"]: x["text"] for x in _tts}
# 10단계가 남긴 subs 에서 숫자 읽기만 뽑는다. 옛 형식(subs 없음)이면 그 씬은 숫자 대조를 못 한다
nums = {x["id"]: [s.get("num") or s["to"] for s in x.get("subs", []) if s["kind"] == "number"] for x in _tts}
no_subs = sorted(x["id"] for x in _tts if "subs" not in x)
only = pick_ids(a.ids, set(ref))
cer = jload(d/"whisper_cer.json") if (d/"whisper_cer.json").exists() else {}
bounds = jload(d/"speech_bounds.json") if (d/"speech_bounds.json").exists() else {}
targets = [sid for sid in sorted(ref) if not only or sid in only]
bad, missing = [], []
for sid in targets:
    f = next((d/f"{sid}{e}" for e in (".wav", ".mp3", ".m4a") if (d/f"{sid}{e}").exists()), None)
    if f is None:
        missing.append(sid); print(f"MISS{sid} 음성 파일 없음: {d}/{sid}.(wav|mp3|m4a)", flush=True); continue
    r = check_scene(f, ref[sid], readings, fixes, num_tokens=nums.get(sid))
    src = f.suffix.lstrip(".")
    out = subprocess.run(["ffmpeg","-i",str(f),"-af","silencedetect=noise=-35dB:d=1.0","-f","null","-"],capture_output=True,text=True).stderr
    sil = list(zip([float(x) for x in re.findall(r"silence_start: ([0-9.]+)",out)],[float(x) for x in re.findall(r"silence_end: ([0-9.]+)",out)]))
    tail_junk = round(r["dur"] - r["last_word_end"], 2)
    cer[sid] = {"cer": r["cer"], "kind": r["kind"], "text": r["text"], "big": r["big"],
                "num_missing": r["num_missing"], "num_checked": len(nums.get(sid) or [])}
    bounds[sid] = {"src": src, "dur": r["dur"], "first_word": r["first_word"], "last_word_end": r["last_word_end"], "last_words": r["last_words"], "silences": sil}
    if r["kind"] == "tail":
        bounds[sid]["suggest_last_word_end"] = r["suggest_last_word_end"]; bounds[sid]["tail_insert"] = r["tail_insert"]
    flag = {"ok": "ok  ", "tail": "TAIL", "content": "BAD "}[r["kind"]]
    extra = f"→ 꼬리 잡음, 실제 끝 {r['suggest_last_word_end']}s 제안 (40단계가 자동 적용)" if r["kind"] == "tail" else (r["big"] if r["big"] else "")
    if r["num_missing"]: extra = f"→ 숫자가 안 들림: {', '.join(r['num_missing'])}  " + (str(extra) if extra else "")
    elif r["cer"] > CER_MAX and r["kind"] == "content" and not r["big"]: extra = f"→ CER {r['cer']:.3f} > {CER_MAX}  " + (str(extra) if extra else "")
    print(f"{flag}{sid} cer {r['cer']:.3f} dur {r['dur']:.1f} speech {r['first_word']:.2f}-{r['last_word_end']:.2f} tail {tail_junk:.1f}s '{r['last_words']}' {extra}", flush=True)
    if not a.quiet_text:
        print(f"    넣은 것 {ref[sid]}", flush=True)
        print(f"    들린 것 {r['hyp']}", flush=True)
    if r["kind"] == "content": bad.append(sid)
jdump(cer, d/"whisper_cer.json"); jdump(bounds, d/"speech_bounds.json")
print(f"검사 {len(targets)-len(missing)}/{len(targets)}씬 (전체 {len(ref)}씬) → {d}/whisper_cer.json")
n_num = sum(len(nums.get(s) or []) for s in targets)
print(f"숫자 읽기 대조 {n_num}개" + (f" · subs 가 없어 대조 못 한 씬 {len(no_subs)}개: {', '.join(no_subs)}" if no_subs else ""))
print("BAD(재생성 대상):", ", ".join(bad) if bad else "none")
if bad: print("  재시도는 자동으로 안 겁니다. 원인을 보고 35_nar_retry.py 를 사람이 거세요 — 시드가 굴러가다 맞으면 원인이 덮입니다.")
if missing: print("검사하지 못함(음성 없음):", ", ".join(missing))
sys.exit(3 if bad or missing else 0)
