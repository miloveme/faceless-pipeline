# 되풀이해 부딪힌 것

**여러 파일에 걸치고, 다시 만날 함정만 여기 적는다.**

한 파일 안에서 끝나는 근거는 **그 값 옆에** 남긴다 — 고치려는 순간에 보여야 뜻이 있다.
무엇을 언제 왜 바꿨는지는 **커밋 로그**다. 여기도 코드 주석도 아니다.

---

## 사설망만 막히는 파이썬 — macOS 로컬 네트워크 권한

**증상.** 공정이 랜의 ComfyUI 에 못 붙는다. 인터넷은 되고, 브라우저로 같은 주소를 열면
열리고, `curl` 로도 열린다. **파이썬만** 즉시 거부된다.

```
프로젝트 파이썬 (uv·conda 둘 다)   Signature=adhoc · TeamIdentifier 없음
  → 랜의 ComfyUI                   No route to host   0.00초   ← 즉시 거부
  → 1.1.1.1:53 (바깥)              열림               0.01초   ← 인터넷은 됨
/usr/bin/python3 (Apple 서명)      → 랜  열림  0.01초
/usr/bin/curl    (Apple 서명)      → 랜  HTTP 200
```

**원인.** macOS 15 부터 **로컬 네트워크 접근 권한이 바이너리마다** 붙는다.
uv·conda 가 깔아 주는 파이썬은 **ad-hoc 서명**(팀 식별자 없음)이라 시스템이 별개 앱으로 보는데,
**권한 목록에 등록조차 안 된다** — 설정을 열어도 켤 항목이 없다.

**가르는 법.** 같은 일을 다른 조건에서 한 번 더 해 본다.

```bash
/usr/bin/env -i /usr/bin/curl -m 4 -s -o /dev/null -w "%{http_code}\n" http://<서버>/system_stats
python3 -c "import socket;socket.create_connection(('<서버IP>',<포트>),3)"
```

`curl` 은 되고 파이썬만 안 되면 이 건이다. **인터넷이 되는 것이 이 함정의 얼굴이다** —
「서버가 죽었나」로 읽히기 때문에 서버·방화벽·VPN 을 먼저 의심하게 된다.

**막는 자리.** `pipeline/net.py` 가 HTTP 를 한 곳으로 모으고 `/usr/bin/curl` 로 나간다.
`hosts.py` · `common.Comfy` · `check_setup.py` · `providers/comfyui_*` 가 전부 그 길을 쓴다.
`elevenlabs` · `openai_tts` 는 바깥 API(https)라 그대로 둔다 — 막히는 것은 사설망뿐이다.

**오류 문구를 뭉개지 마라.** 전에는 `URLError` 한 낱말만 남겨서
「서버가 죽었다」와 「내 쪽이 막혔다」를 못 갈랐다. `net.py` 는 `curl` 의 종료코드와 문장을 그대로 싣는다.

**언젠가 풀린다면.** 파이썬이 붙는 환경(Apple 서명 빌드, 또는 권한이 붙는 배포)으로 옮기면
`net.py` 의 `_curl()` 안만 `urllib` 로 되돌리면 된다. 부르는 쪽은 안 바뀐다 — 그러라고 모았다.

---

## 어느 파이썬으로 도는지 정해 두지 않으면 창마다 다르게 실패한다

**증상.** 같은 스크립트가 창에 따라 되기도 하고 `ModuleNotFoundError` 로 죽기도 한다.
의존이 반쯤 있는 환경에서는 **더 나쁘다** — 죽지 않고 다르게 돈다.

**원인.** `python3` 가 무엇을 가리키는지가 **셸이 뜬 순서와 PATH** 에 달려 있었다.

**막는 자리 둘.**

```
pipeline/_py.sh     셸 스크립트가 읽는다. `.venv` 가 없으면 종료코드 2 로 멈춘다
pipeline/common.py  파이썬 스크립트 29개가 거쳐 간다. 프로젝트 `.venv` 가 아니면 종료코드 2
```

**「없으면 전역 python3 로」는 안 한다.** 그게 갈리던 원인이다.
문서 스무 곳이 `python3 pipeline/...` 라고 적어 둔 것을 다 고치는 대신 관문을 뒀다 —
`source .venv/bin/activate` 뒤에는 그 문서가 그대로 맞는다.

일부러 다른 환경에서 돌려야 하면 `FACELESS_ALLOW_ANY_PYTHON=1`.

환경을 바꾸는 것은 `.venv` 를 다시 만드는 것이지 저 두 파일을 고치는 것이 아니다.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```
