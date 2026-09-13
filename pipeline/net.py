"""ComfyUI 서버로 나가는 HTTP 한 곳. **`curl` 로 나간다 — 파이썬 소켓이 아니다.**

## 왜 `curl` 인가

2026-09-13 에 공정이 사설망의 ComfyUI 에 못 붙었다. 브라우저는 되고 `curl` 도 되는데
파이썬만 즉시 거부됐다. 재서 가른 것:

```
프로젝트 파이썬 (uv·conda 둘 다)   Signature=adhoc · TeamIdentifier 없음
  → 랜의 ComfyUI                   No route to host   0.00초   ← 즉시 거부
  → 1.1.1.1:53 (바깥)              열림               0.01초   ← 인터넷은 됨
/usr/bin/python3 (Apple 서명)      → 랜  열림  0.01초
/usr/bin/curl    (Apple 서명)      → 랜  HTTP 200
```
(주소는 사람마다 달라 여기 안 적는다 — `voice.json` 의 `hosts` 에 있다)

macOS 15+ 의 **로컬 네트워크 권한은 바이너리마다** 붙는다. anaconda 파이썬은 ad-hoc 서명이라
시스템이 별개 앱으로 보는데, **권한 목록에 등록조차 안 돼서** 사용자가 켤 수도 없다.
사설망만 막히고 인터넷은 열린다 — 그래서 「서버가 죽었나」로 오해하기 쉽다.

세 번을 헛짚었다(샌드박스 · macOS 권한 · VPN). 답이 나온 것은 `env -i` 로 **같은 일을
다른 조건에서 한 번 더 해 본** 뒤였다. 고치기 전후를 실물로 재는 그 방법이 인프라에서도 같다.

**이 저장소는 이미 참조 음성 업로드를 `curl` 로 하고 있었다**(`comfyui_chatterbox.py`).
새 방식이 아니라 이미 있던 방식을 나머지 호출로 넓힌 것이다.

## 고칠 일이 생기면

파이썬 쪽이 붙는 환경으로 옮겨 가면 `_curl()` 안만 `urllib` 로 되돌리면 된다.
부르는 쪽은 안 바뀐다 — 그러라고 여기 모았다.
"""
import json
import pathlib
import subprocess

CURL = "/usr/bin/curl"          # **Apple 서명 바이너리를 지목한다.** PATH 의 curl 은
                                # conda 가 깔아 둔 것일 수 있고 그건 같은 벽에 막힌다.


class NetError(RuntimeError):
    """서버에 못 붙었거나 응답이 JSON 이 아니다. 부르는 쪽은 이것만 잡으면 된다."""


def _curl(args, timeout, what):
    try:
        p = subprocess.run([CURL, "-sS", "-m", str(timeout), *args],
                           capture_output=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        raise NetError(f"{what}: {timeout}초 안에 응답 없음")
    if p.returncode != 0:
        raise NetError(f"{what}: curl {p.returncode} · {p.stderr.decode(errors='replace').strip()[:200]}")
    return p.stdout


def get_json(url, timeout=10):
    """GET → dict. 실패는 전부 NetError 로 모은다."""
    raw = _curl([url], timeout, f"GET {url}")
    try:
        return json.loads(raw)
    except ValueError:
        raise NetError(f"GET {url}: JSON 이 아님 · 앞 120자 {raw[:120]!r}")


def post_json(url, data, timeout=30):
    """POST(JSON) → dict."""
    raw = _curl(["-H", "Content-Type: application/json",
                 "--data-binary", "@-", url], timeout, f"POST {url}")
    try:
        return json.loads(raw)
    except ValueError:
        raise NetError(f"POST {url}: JSON 이 아님 · 앞 120자 {raw[:120]!r}")


def post_json_body(url, data, timeout=30):
    """POST(JSON) → dict. 본문을 stdin 으로 넣는다 — 인자 길이 제한을 안 탄다.

    워크플로 JSON 은 수십 KB 가 되므로 `--data-binary @-` 로 stdin 을 쓴다.
    명령줄에 실으면 길이 제한에 걸리고, 임시 파일은 지울 책임이 생긴다.
    """
    body = json.dumps(data).encode()
    try:
        p = subprocess.run([CURL, "-sS", "-m", str(timeout),
                            "-H", "Content-Type: application/json",
                            "--data-binary", "@-", url],
                           input=body, capture_output=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        raise NetError(f"POST {url}: {timeout}초 안에 응답 없음")
    if p.returncode != 0:
        raise NetError(f"POST {url}: curl {p.returncode} · {p.stderr.decode(errors='replace').strip()[:200]}")
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise NetError(f"POST {url}: JSON 이 아님 · 앞 120자 {p.stdout[:120]!r}")


def download(url, out_path, timeout=180):
    """파일 하나를 받아 저장한다. **받은 뒤 크기를 본다** — 0 바이트는 성공이 아니다."""
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _curl(["-o", str(out), url], timeout, f"GET {url}")
    if not out.exists() or out.stat().st_size == 0:
        raise NetError(f"GET {url}: 받은 파일이 비었습니다 ({out})")
    return out


def upload_file(host, local_path, upload_name, kind="input", timeout=60):
    """ComfyUI `/upload/image` 로 파일 하나를 올린다(소리 파일도 이 경로를 쓴다)."""
    return _curl(["-F", f"image=@{local_path}", "-F", f"type={kind}",
                  "-F", "overwrite=true", host.rstrip('/') + "/upload/image"],
                 timeout, f"UPLOAD {upload_name}")
