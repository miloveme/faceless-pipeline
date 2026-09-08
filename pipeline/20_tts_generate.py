#!/usr/bin/env python3
"""씬별 내레이션 생성 → audio/nar_raw/<id>.mp3

어느 서비스로 만들지는 voice.json 의 `provider` 가 정하고, 설정은 providers[<이름>] 블록입니다.

comfyui_chatterbox 일 때: 서버는 그 블록의 `hosts` 순서대로 씁니다. 앞이 기본(원격), 뒤가 대비(로컬).
응답이 없거나 큐가 길면 건너뛰고, 쓸 수 있는 서버가 여럿이면 나눠서 동시에 돌립니다.
한 서버가 도중에 죽으면 그 씬은 다른 서버로 넘깁니다.
다른 제공자(API·shell)에는 서버 개념이 없어 순차로 만듭니다. `--host` 는 comfyui_chatterbox 전용입니다.

사용: 20_tts_generate.py <EP> [--ids s01,s02] [--seed N] [--host <주소>] [--serial]
"""
import argparse, threading, queue, time
from common import *
from hosts import plan

# **안 준 것과 빈 것을 가른다.** default 를 "" 로 두면 --ids 를 안 줘도 pick_ids 가
# 「비어 있다」로 죽인다 — 네 스크립트가 다 그랬다(음악 감독이 잡았다). 기본은 None 이다.
ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids")
ap.add_argument("--seed", type=int); ap.add_argument("--host", default="", help="서버를 직접 지정")
ap.add_argument("--serial", action="store_true", help="한 대만 써서 순차 생성")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep)
v = voice_cfg(); pname = provider_name(v); pcfg = provider_cfg(v, pname)   # 설정은 생성 전에 검증한다
if a.seed is not None:
    v = {**v, "providers": {**v["providers"], pname: {**pcfg, "seed": a.seed}}}
    pcfg = v["providers"][pname]

if not p["tts_input"].exists(): die(f"읽기 전처리 결과가 없습니다: {p['tts_input']}\n  먼저 10_tts_prep.py 를 돌리세요.")
tts = jload(p["tts_input"]); only = pick_ids(a.ids, {x["id"] for x in tts})
todo = [x for x in tts if not only or x["id"] in only]
if not todo: die("생성할 씬이 없습니다.")
p["nar_raw"].mkdir(parents=True, exist_ok=True)

# 시작 전 반드시 연결을 확인하고 계획을 세운다 (자체 호스팅 ComfyUI 일 때만 서버 개념이 있다)
if pname == "comfyui_chatterbox":
    if a.host:
        hosts = [a.host]; print(f"서버 지정: {a.host}\n")
    else:
        hosts, _ = plan(pcfg, n_items=len(todo), total_chars=sum(len(x["text"]) for x in todo),
                        verbose=True, serial=a.serial)
else:
    if a.host: die("--host 는 comfyui_chatterbox 에서만 씁니다.", 2)
    hosts = [None]                       # API 제공자는 서버를 고르지 않는다
    print(f"제공자: {pname} · {len(todo)}씬 순차 생성\n")

workers = hosts

jobs = queue.Queue()
for x in todo: jobs.put(x)
lock = threading.Lock()
times, failed = {}, []
t0 = time.time()

def work(host):
    tag = host.split("//")[-1].split(":")[0] if host else pname
    while True:
        try: x = jobs.get_nowait()
        except queue.Empty: return
        out = p["nar_raw"]/f"{x['id']}.mp3"
        try:
            ex = tts_generate(x["text"], out, v, host=host)
            with lock:
                times[x["id"]] = ex
                print(f"  {x['id']} ok {dur(out):.1f}s (생성 {ex}s · {tag})", flush=True)
        except SystemExit:
            raise
        except Exception as e:
            with lock:
                print(f"  {x['id']} 실패 [{tag}] {e}", flush=True)
                failed.append((x["id"], host))
                n_fail = len([f for f in failed if f[1] == host])
            jobs.put(x)                      # 다른 서버가 집어가도록 되돌린다
            if n_fail >= 2:
                with lock: print(f"  {tag} 연속 실패 — 이 서버는 뺍니다", flush=True)
                return
            time.sleep(2)

ths = [threading.Thread(target=work, args=(w,), daemon=True) for w in workers]
for t in ths: t.start()
for t in ths: t.join()

path = p["nar_raw"]/"exec_times.json"
old = jload(path) if path.exists() else {}
old.update(times); jdump(old, path)
left = [x["id"] for x in todo if x["id"] not in times]
print(f"\n{len(times)}/{len(todo)}씬 생성 (전체 {len(tts)}씬) · {round(time.time()-t0)}초 · {pname} · 작업자 {len(workers)}")
if left: die("생성하지 못한 씬: " + ", ".join(left))
