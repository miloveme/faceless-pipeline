# 공정이 쓸 파이썬을 **한 곳에서** 정한다. 셸 스크립트가 `. "$HERE/_py.sh"` 로 읽는다.
#
# 프로젝트 `.venv` 가 없으면 **멈춘다** — 「없으면 전역 python3 로」는 안 한다.
# 그러면 창마다 다른 환경에서 돌고 의존이 반쯤 있으면 조용히 다르게 실패한다.
# → `docs/PITFALLS.md` 「어느 파이썬으로 도는지 정해 두지 않으면」
#
# 파이썬을 바꾸는 것은 `.venv` 를 다시 만드는 것이지 이 파일을 고치는 것이 아니다.
_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
PY="$_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: 가상환경이 없습니다 — $PY" >&2
  echo "  만드세요:  uv venv --python 3.12 .venv" >&2
  echo "            uv pip install --python .venv/bin/python -r requirements.txt" >&2
  exit 2
fi
export PY
