"""ComfyUI 의 Qwen3-TTS 로 내레이션을 만든다 (AILab QwenTTS 노드팩).

`comfyui_chatterbox.py` 와 **같은 자리에 끼워 쓴다** — `voice.json` 의 `provider` 한 줄만
`comfyui_qwen3` 로 바꾸면 공정의 다른 단계는 안 건드린다. 그러라고 제공자를 갈라 두었다.

## chatterbox 와 무엇이 다른가

```
chatterbox   FL_ChatterboxMultilingualTTS 한 노드가 참조 음성을 직접 물었다
qwen3        LoadAudio → AILab_Qwen3TTSVoiceClone_Advanced → SaveAudioMP3  **세 노드**
```

- **`reference_text` 가 새로 있다.** 참조 음성에서 **실제로 무슨 말을 하는지** 적어 주면
  복제가 정확해진다. 비워도 돌지만 정확도가 떨어진다. `voice.json` 의 `ref_text` 로 받는다.
- **표현 손잡이가 다르다.** chatterbox 의 `exaggeration`·`cfg_weight` 가 없고
  `temperature`·`top_p`·`top_k`·`repetition_penalty` 다. **값을 옮겨 적지 마라** —
  이름이 겹쳐도(temperature) 같은 뜻이 아니다.
- **`do_sample` 이 기본 False.** 끄면 시드가 결과를 안 바꾼다. 재생성으로 다른 판을
  얻으려면 켜야 한다 — 그래서 여기서는 **기본을 True 로 둔다**(`voice.json` 에서 덮을 수 있다).
- **말 속도를 직접 정하는 입력이 어느 쪽에도 없다.** 이 제공자를 만든 이유가 속도였는데,
  파라미터로는 못 고치고 **모델이 바뀌어야** 달라진다. 그래서 둘을 나란히 듣고 고른다.

## 잠금

`voice.json` 의 소리 키는 잠금이다. 재생성이 필요하면 **시드만** 바꾼다 —
`20_tts_generate.py <EP> --seed N` 이거나 `35_nar_retry.py <EP> --ids <씬> --tries N`.
`retry_seeds` 를 `attempt` 가 차례로 훑는 구조는 chatterbox 와 같다.
"""
import json
import pathlib
import shutil
import tempfile
import time

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from net import get_json, post_json_body, download, upload_file  # noqa: E402


def _upload_ref(host, cfg, base_dir):
    """참조 음성을 서버로 올린다. **`/upload/image` 가 맞다** — ComfyUI 는 소리도 그 경로로 받는다."""
    src = (base_dir / cfg["ref_file"]).expanduser()
    if not src.exists():
        raise SystemExit(f"참조 음성이 없습니다: {src}\n  docs/RECORDING.md 를 보고 만든 뒤 이 경로에 두세요.")
    tmp = pathlib.Path(tempfile.gettempdir()) / cfg["ref_upload_name"]
    shutil.copy(src, tmp)
    upload_file(host, tmp, cfg["ref_upload_name"], kind="input", timeout=60)


def generate(text, out_path, cfg, attempt=0, _uploaded={}, host=None):
    """한 씬을 만든다. 규약은 chatterbox 와 같다 — 부르는 쪽(20·35 단계)이 안 바뀐다."""
    if host is None:
        import pathlib as _p
        sys.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from hosts import pick
        host = pick(cfg, need=1, verbose=False)[0]
    host = host.rstrip("/")

    base_dir = pathlib.Path(__file__).resolve().parent.parent
    if host not in _uploaded:
        _upload_ref(host, cfg, base_dir)
        _uploaded[host] = True

    # **시드는 `[seed] + retry_seeds` 를 `attempt` 가 훑는다** — chatterbox 와 같은 규칙이라
    # 두 제공자를 오갈 때 「몇 번째 시도가 어느 시드였나」가 안 갈린다.
    seeds = [cfg.get("seed", 0)] + list(cfg.get("retry_seeds", []))
    seed = seeds[min(attempt, len(seeds) - 1)]

    wf = {
        "1": {"class_type": "LoadAudio",
              "inputs": {"audio": cfg["ref_upload_name"]}},
        "2": {"class_type": cfg.get("node", "AILab_Qwen3TTSVoiceClone_Advanced"), "inputs": {
            "target_text": text,
            "model_size": cfg.get("model_size", "1.7B"),
            "device": cfg.get("device", "auto"),
            "precision": cfg.get("precision", "bf16"),
            "language": cfg.get("language", "Korean"),
            "reference_audio": ["1", 0],
            # 비어 있으면 키를 안 보낸다 — 빈 문자열을 주는 것과 안 주는 것이 다를 수 있다.
            **({"reference_text": cfg["ref_text"]} if cfg.get("ref_text") else {}),
            "x_vector_only": cfg.get("x_vector_only", False),
            "max_new_tokens": cfg.get("max_new_tokens", 2048),
            # **기본 True 다.** False 면 시드가 결과를 안 바꿔 재생성이 뜻을 잃는다.
            "do_sample": cfg.get("do_sample", True),
            "top_p": cfg.get("top_p", 0.9),
            "top_k": cfg.get("top_k", 50),
            "temperature": cfg.get("temperature", 0.9),
            "repetition_penalty": cfg.get("repetition_penalty", 1.0),
            "attention": cfg.get("attention", "auto"),
            # **모델을 안 내린다.** 씬마다 내렸다 올리면 31씬에서 그 시간이 통째로 붙는다.
            "unload_models": cfg.get("unload_models", False),
            "seed": seed}},
        "3": {"class_type": "SaveAudioMP3", "inputs": {
            "audio": ["2", 0],
            "filename_prefix": "tts/" + pathlib.Path(out_path).stem,
            "quality": cfg.get("mp3_quality", "V0")}},
    }

    r = post_json_body(host + "/prompt", {"prompt": wf}, timeout=30)
    if r.get("node_errors"):
        raise SystemExit("ComfyUI node_errors: " + json.dumps(r["node_errors"], ensure_ascii=False)[:400])
    if "prompt_id" not in r:
        raise SystemExit("ComfyUI 가 prompt_id 를 안 줬습니다: " + json.dumps(r, ensure_ascii=False)[:300])

    pid, t0 = r["prompt_id"], time.time()
    while time.time() - t0 < cfg.get("timeout_sec", 900):
        h = get_json(f"{host}/history/{pid}", timeout=30)
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("ComfyUI 실행 오류: " + json.dumps(st, ensure_ascii=False)[:400])
            files = [f for o in h[pid].get("outputs", {}).values() for f in o.get("audio", [])]
            if files:
                f = files[0]
                url = (f"{host}/view?filename={f['filename']}&subfolder={f.get('subfolder','')}"
                       f"&type={f.get('type','output')}")
                download(url, out_path, timeout=180)
                ts = {m[0]: m[1].get("timestamp") for m in st.get("messages", [])
                      if isinstance(m, (list, tuple)) and len(m) > 1 and isinstance(m[1], dict)}
                if "execution_start" in ts and "execution_success" in ts:
                    return (ts["execution_success"] - ts["execution_start"]) / 1000.0
                return time.time() - t0
        time.sleep(1.0)
    raise TimeoutError(f"{cfg.get('timeout_sec', 900)}초 안에 안 끝났습니다 (prompt_id {pid})")
