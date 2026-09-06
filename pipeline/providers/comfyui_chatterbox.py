"""자체 호스팅 ComfyUI + Chatterbox 다국어 TTS 노드.

장점: 참조 음성 하나로 화자를 고정, 로컬 GPU면 비용 0.
필요: ComfyUI 실행 + 커스텀 노드 팩(Manager 에서 'chatterbox' 검색).
cfg 예시는 voice.example.json 의 providers.comfyui_chatterbox 참고.
"""
import json, pathlib, shutil, tempfile, time, urllib.request, subprocess

def _post(host, path, data):
    req = urllib.request.Request(host + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def _upload_ref(host, cfg, base_dir):
    src = (base_dir / cfg["ref_file"]).expanduser()
    if not src.exists():
        raise SystemExit(f"참조 음성이 없습니다: {src}\n  docs/RECORDING.md 를 보고 만든 뒤 이 경로에 두세요.")
    tmp = pathlib.Path(tempfile.gettempdir()) / cfg["ref_upload_name"]
    shutil.copy(src, tmp)
    subprocess.run(["curl", "-sS", "-m", "60", "-F", f"image=@{tmp}", "-F", "type=input",
                    "-F", "overwrite=true", host + "/upload/image"],
                   check=True, stdout=subprocess.DEVNULL)

def generate(text, out_path, cfg, attempt=0, _uploaded={}):
    host = cfg["host"].rstrip("/")
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
        h = json.loads(urllib.request.urlopen(f"{host}/history/{pid}", timeout=30).read())
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("ComfyUI 실행 오류: " + json.dumps(st)[:400])
            files = [f for o in h[pid].get("outputs", {}).values() for f in o.get("audio", [])]
            if files:
                f = files[0]
                url = (f"{host}/view?filename={f['filename']}&subfolder={f.get('subfolder','')}"
                       f"&type={f.get('type','output')}")
                pathlib.Path(out_path).write_bytes(urllib.request.urlopen(url, timeout=180).read())
                ts = {m[0]: m[1].get("timestamp") for m in st.get("messages", [])
                      if isinstance(m, list) and len(m) > 1 and isinstance(m[1], dict)}
                s, e = ts.get("execution_start"), ts.get("execution_success")
                return round((e - s) / 1000, 1) if s and e else None
        time.sleep(3)
    raise TimeoutError(pid)
