#!/usr/bin/env python3
"""씬별 내레이션 생성 → audio/nar_raw/<id>.mp3

서버는 voice.json 의 `hosts` 순서대로 씁니다. 앞이 기본(원격), 뒤가 대비(로컬).
응답이 없거나 큐가 길면 건너뛰고, 쓸 수 있는 서버가 여럿이면 나눠서 동시에 돌립니다.
한 서버가 도중에 죽으면 그 씬은 다른 서버로 넘깁니다.

사용: 20_tts_generate.py <EP> [--ids s01,s02] [--seed N] [--host <주소>] [--serial]
"""
import argparse, threading, queue, time
from common import *
from hosts import pick

ap = argparse.ArgumentParser(); ap.add_argument("ep"); ap.add_argument("--ids", default="")
ap.add_argument("--seed", type=int); ap.add_argument("--host", default="", help="서버를 직접 지정")
ap.add_argument("--serial", action="store_true", help="한 대만 써서 순차 생성")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); v = voice_cfg()

tts = jload(p["tts_input"]); only = set(a.ids.split(",")) if a.ids else None
todo = [x for x in tts if not only or x["id"] in only]
p["nar_raw"].mkdir(parents=True, exist_ok=True)

print("서버 상태")
if a.host:
    hosts = [a.host]; print(f"  → 지정: {a.host}")
else:
    v2 = dict(v);  v2["parallel"] = v.get("parallel", True) and not a.serial
    hosts = pick(v2, need=len(todo))

workers = [(h, h) for h in hosts]

jobs = queue.Queue()
for x in todo: jobs.put(x)
lock = threading.Lock()
times, failed = {}, []
t0 = time.time()

def work(host, c):
    while True:
        try: x = jobs.get_nowait()
        except queue.Empty: return
        out = p["nar_raw"]/f"{x['id']}.mp3"
        try:
            ex = tts_generate(x["text"], out, v, attempt=0, host=c)
            with lock:
                times[x["id"]] = ex
                tag = host.split("//")[-1].split(":")[0]
                print(f"  {x['id']} ok {dur(out):.1f}s (생성 {ex}s · {tag})", flush=True)
        except Exception as e:
            with lock: print(f"  {x['id']} 실패 [{host}] {e}", flush=True)
            jobs.put(x)                      # 다른 서버가 집어가도록 되돌린다
            failed.append((x["id"], host))
            if len([f for f in failed if f[1] == host]) >= 2:
                with lock: print(f"  {host} 연속 실패 — 이 서버는 뺍니다", flush=True)
                return
            time.sleep(2)

ths = [threading.Thread(target=work, args=w, daemon=True) for w in workers]
for t in ths: t.start()
for t in ths: t.join()

path = p["nar_raw"]/"exec_times.json"
old = jload(path) if path.exists() else {}
old.update(times); jdump(old, path)
left = [x["id"] for x in todo if x["id"] not in times]
print(f"\n{len(times)}/{len(todo)}개 생성 · {round(time.time()-t0)}초 · 서버 {len(workers)}대")
if left: die("생성하지 못한 씬: " + ", ".join(left))
