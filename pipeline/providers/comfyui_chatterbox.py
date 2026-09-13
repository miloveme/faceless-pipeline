"""자체 호스팅 ComfyUI + Chatterbox 다국어 TTS 노드.

장점: 참조 음성 하나로 화자를 고정, 로컬 GPU면 비용 0.
필요: ComfyUI 실행 + 커스텀 노드 팩(Manager 에서 'chatterbox' 검색).
cfg 예시는 voice.example.json 의 providers.comfyui_chatterbox 참고.
"""
import json, pathlib, shutil, tempfile, time

# **HTTP 는 `net.py` 한 곳으로.** 이 파일은 이미 업로드만 `curl` 로 하고 있었는데
# 나머지 호출도 같은 길로 모았다 — anaconda 파이썬은 사설망에 못 붙는다(net.py 머리 참고).
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from net import get_json, post_json_body, download, upload_file, NetError  # noqa: E402

def _post(host, path, data):
    return post_json_body(host + path, data, timeout=30)

def _upload_ref(host, cfg, base_dir):
    src = (base_dir / cfg["ref_file"]).expanduser()
    if not src.exists():
        raise SystemExit(f"참조 음성이 없습니다: {src}\n  docs/RECORDING.md 를 보고 만든 뒤 이 경로에 두세요.")
    tmp = pathlib.Path(tempfile.gettempdir()) / cfg["ref_upload_name"]
    shutil.copy(src, tmp)
    upload_file(host, tmp, cfg["ref_upload_name"], kind="input", timeout=60)

def generate(text, out_path, cfg, attempt=0, _uploaded={}, host=None):
    # host 를 지정하지 않으면 hosts 중에서 고른다 (앞이 기본, 막히면 다음)
    if host is None:
        import sys, pathlib as _pl
        sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
        from hosts import pick
        host = pick(cfg, need=1, verbose=False)[0]
    host = host.rstrip("/")
    base = pathlib.Path(__file__).resolve().parent.parent          # pipeline/
    if host not in _uploaded:
        _upload_ref(host, cfg, base); _uploaded[host] = True
    seeds = [cfg.get("seed", 0)] + list(cfg.get("retry_seeds", []))
    seed = seeds[min(attempt, len(seeds) - 1)]
    wf = {
        "1": {"class_type": "LoadAudio", "inputs": {"audio": cfg["ref_upload_name"]}},
        "2": {"class_type": cfg.get("node", "FL_ChatterboxMultilingualTTS"), "inputs": {
            "text": text, "language": cfg.get("language", "Korean (ko)"),
            "exaggeration": cfg.get("exaggeration", 0.3), "cfg_weight": cfg.get("cfg_weight", 0.5),
            "temperature": cfg.get("temperature", 0.7), "repetition_penalty": cfg.get("repetition_penalty", 2.0),
            "min_p": cfg.get("min_p", 0.05), "top_p": cfg.get("top_p", 1.0), "seed": seed,
            "audio_prompt": ["1", 0], "use_cpu": False, "keep_model_loaded": True}},
        "3": {"class_type": "SaveAudioMP3", "inputs": {"audio": ["2", 0],
              "filename_prefix": "tts/" + pathlib.Path(out_path).stem, "quality": "V0"}},
    }
    r = _post(host, "/prompt", {"prompt": wf})
    if r.get("node_errors"):
        raise SystemExit("ComfyUI node_errors: " + json.dumps(r["node_errors"])[:400])
    pid, t0 = r["prompt_id"], time.time()
    while time.time() - t0 < cfg.get("timeout_sec", 900):
        h = get_json(f"{host}/history/{pid}", timeout=30)
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("ComfyUI 실행 오류: " + json.dumps(st)[:400])
            files = [f for o in h[pid].get("outputs", {}).values() for f in o.get("audio", [])]
            if files:
                f = files[0]
                url = (f"{host}/view?filename={f['filename']}&subfolder={f.get('subfolder','')}"
                       f"&type={f.get('type','output')}")
                download(url, out_path, timeout=180)
                ts = {m[0]: m[1].get("timestamp") for m in st.get("messages", [])
                      if isinstance(m, list) and len(m) > 1 and isinstance(m[1], dict)}
                s, e = ts.get("execution_start"), ts.get("execution_success")
                return round((e - s) / 1000, 1) if s and e else None
        time.sleep(3)
    raise TimeoutError(pid)
