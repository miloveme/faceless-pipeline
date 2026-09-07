"""ComfyUI 서버 여러 대를 확인하고 작업을 배분한다.

**작업을 시작하기 전에 항상 연결을 확인한다.** 죽은 서버에 던져 놓고 기다리는 것이
가장 흔한 시간 낭비다. 확인 → 쓸 서버 결정 → 계획 출력 → 실행 순서로 간다.

원칙
- `hosts` 순서가 우선순위. 앞이 기본.
- 응답이 없거나 큐가 `max_queue` 보다 길면 건너뛴다.
- 쓸 수 있는 서버가 여럿이면 나눠서 동시에 돌린다(먼저 끝난 쪽이 다음 것을 집어가는 방식).
- 전부 바쁘면 가장 덜 바쁜 한 대에 맡긴다. 기다리는 게 안 하는 것보다 낫다.
"""
import json, time, urllib.request

DEFAULT_CPS = 8.4          # 실측 처리량(초당 글자). 서버 성능 차가 크지 않았다.

def probe(host, timeout=4):
    """서버 하나를 확인한다. → dict(alive, queue, gpu, err)"""
    h = host.rstrip("/")
    out = {"host": h, "alive": False, "queue": None, "gpu": None, "err": None}
    try:
        q = json.loads(urllib.request.urlopen(h + "/queue", timeout=timeout).read())
        out["alive"] = True
        out["queue"] = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
    except Exception as e:
        out["err"] = type(e).__name__; return out
    try:
        s = json.loads(urllib.request.urlopen(h + "/system_stats", timeout=timeout).read())
        d = (s.get("devices") or [{}])[0]
        out["gpu"] = d.get("name", "?").split(":")[0][:28]
    except Exception:
        pass
    return out

def survey(cfg, timeout=4):
    hosts = cfg.get("hosts") or ([cfg["host"]] if cfg.get("host") else [])
    if not hosts: raise SystemExit("voice.json 에 hosts 가 없습니다.")
    return [probe(h, timeout) for h in hosts]

def plan(cfg, n_items=1, total_chars=None, verbose=True, serial=False):
    """확인 → 쓸 서버 결정 → 계획. 반환: (쓸 서버 목록, 상태 목록)"""
    st = survey(cfg)
    maxq = cfg.get("max_queue", 2)
    if verbose:
        print("서버 확인")
        for s in st:
            if s["alive"]:
                print(f"  {s['host']:32} 큐 {s['queue']}" + (f" · {s['gpu']}" if s["gpu"] else ""))
            else:
                print(f"  {s['host']:32} 응답 없음 ({s['err']})")
    free = [s["host"] for s in st if s["alive"] and s["queue"] <= maxq]
    note = ""
    if not free:
        busy = sorted((s["queue"], s["host"]) for s in st if s["alive"])
        if not busy:
            tried = "\n".join(f"    {s['host']}  ({s['err']})" for s in st)
            raise SystemExit(
                "쓸 수 있는 ComfyUI 서버가 없습니다. 확인한 주소:\n" + tried +
                "\n  서버가 꺼져 있거나 주소가 다릅니다. 주소는 사람마다 달라 저장소에 없습니다."
                "\n  추측하거나 포트를 훑지 말고, 무엇을 하려다 무슨 응답을 받았는지 적어 엔지니어에게 넘기세요."
                "\n  (주소를 아는 사람은 사용자입니다. voice.json 의 hosts 를 고치는 것도 엔지니어 일입니다.)")
        free = [busy[0][1]]; note = " (전부 바쁨 — 가장 덜 바쁜 곳에 맡김)"
    if serial or not cfg.get("parallel", True) or n_items <= 1:
        free = free[:1]
    if verbose:
        print(f"\n작업 계획")
        print(f"  항목 {n_items}개 · 서버 {len(free)}대{note}")
        for h in free: print(f"    {h}")
        if total_chars:
            cps = cfg.get("chars_per_sec", DEFAULT_CPS)
            est = total_chars / cps / len(free)
            print(f"  예상 {est/60:.1f}분 (초당 {cps}자 기준, {len(free)}대 분산)")
        print()
    return free, st

# 옛 이름 유지
def pick(cfg, need=1, verbose=True):
    return plan(cfg, n_items=need, verbose=verbose)[0]
