# 공정이 쓸 파이썬을 **한 곳에서** 정한다. 셸 스크립트가 `. "$HERE/_py.sh"` 로 읽는다.
#
# ## 왜 있나
#
# 2026-09-13 에 anaconda 에서 uv 로 갈아탔다. 그전에는 `python3` 가 어느 파이썬을
# 가리키는지가 **셸이 뜬 순서와 PATH 에 달려 있었고**, 그래서 같은 스크립트가
# 창마다 다른 환경에서 돌았다. 의존이 한쪽에만 있으면 조용히 다르게 실패한다.
#
# **가상환경을 못박는다.** 프로젝트의 `.venv` 가 있으면 그것을 쓰고, 없으면 멈춘다 —
# 「없으면 전역 python3 로」는 안 한다. 그게 바로 갈리던 원인이다.
#
# ## 고칠 일이 생기면
#
# 파이썬을 바꾸는 것은 `.venv` 를 다시 만드는 것이지 이 파일을 고치는 것이 아니다.
#   uv venv --python 3.12 .venv
#   uv pip install --python .venv/bin/python -r requirements.txt
_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
PY="$_ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: 가상환경이 없습니다 — $PY" >&2
  echo "  만드세요:  uv venv --python 3.12 .venv" >&2
  echo "            uv pip install --python .venv/bin/python -r requirements.txt" >&2
  exit 2
fi
export PY
