"""ComfyUI 서버로 나가는 HTTP 한 곳. **`curl` 로 나간다 — 파이썬 소켓이 아니다.**

ad-hoc 서명 파이썬(uv·conda)은 macOS 의 로컬 네트워크 권한을 못 받아 **사설망에만** 못 붙는다.
인터넷은 열려 있어서 「서버가 죽었나」로 읽히는 것이 이 함정의 얼굴이다.
증상·가르는 법·언젠가 되돌리는 법은 → `docs/PITFALLS.md` 「사설망만 막히는 파이썬」.

부르는 쪽은 `get_json` · `post_json_body` · `download` · `upload_file` 넷만 쓴다.
**오류는 `NetError` 하나로 모으고 `curl` 의 문장을 그대로 싣는다** — 한 낱말로 뭉개면
「서버가 죽었다」와 「내 쪽이 막혔다」를 못 가른다.
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
