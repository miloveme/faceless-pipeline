"""ComfyUI 서버 여러 대를 골라 쓰는 도우미.

원칙
- voice.json 의 `hosts` 순서가 우선순위다. 앞에 있는 것이 기본.
- 응답이 없거나 큐가 `max_queue` 보다 길면 건너뛴다.
- 쓸 수 있는 서버가 여러 대면 나눠서 동시에 돌린다.
- 전부 막혀 있으면 가장 덜 바쁜 서버 하나에 그냥 맡긴다(기다리는 게 안 하는 것보다 낫다).
"""
import json, urllib.request

def _probe(host, timeout=4):
    """(살아있나, 큐 길이). 응답 없으면 (False, None)."""
    try:
        q = json.loads(urllib.request.urlopen(host.rstrip("/") + "/queue", timeout=timeout).read())
        return True, len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
    except Exception:
        return False, None

def pick(cfg, need=1, verbose=True):
    """쓸 서버 목록을 우선순위대로 돌려준다. need = 만들 씬 수."""
    hosts = cfg.get("hosts") or ([cfg["host"]] if cfg.get("host") else [])
    if not hosts: raise SystemExit("voice.json 에 hosts 가 없습니다.")
    maxq = cfg.get("max_queue", 2)
    status = [(h, *_probe(h)) for h in hosts]
    if verbose:
        for h, alive, q in status:
            print(f"  {h:32} {'큐 ' + str(q) if alive else '응답 없음'}")
    free = [h for h, alive, q in status if alive and q <= maxq]
    if not free:
        busy = [(q, h) for h, alive, q in status if alive]
        if not busy: raise SystemExit("쓸 수 있는 ComfyUI 서버가 없습니다.")
        busy.sort(); free = [busy[0][1]]
        if verbose: print(f"  → 전부 바쁨. 가장 덜 바쁜 {free[0]} 에 맡깁니다.")
    if not cfg.get("parallel", True) or need <= 1:
        free = free[:1]
    if verbose:
        print(f"  → 사용: {', '.join(free)}" + (f" (동시 {len(free)}대)" if len(free) > 1 else ""))
    return free
