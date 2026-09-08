#!/usr/bin/env python3
"""에피소드 데이터를 Remotion 프로젝트로 복사: public/<slug>/nar/<id>.mp3, src/<slug>/data/{scenes_v2,captions}.json
소재 경로도 함께 검사한다 — 남의 편 소재를 가리켜도 컴파일과 렌더는 되기 때문에 여기서 센다.
사용: 55_remotion_sync.py <EP> [--skip-src-check]"""
import argparse, shutil, re
from common import *
ap = argparse.ArgumentParser(); ap.add_argument("ep")
ap.add_argument("--skip-src-check", action="store_true", help="소재 경로 검사를 건너뛴다(컴포넌트를 아직 쓰는 중이거나, 검사가 잘못 잡을 때)")
a = ap.parse_args(); ep = ep_dir(a.ep); p = P(ep); sl = slug(ep)

MEDIA = r"mp4|mov|webm|png|jpg|jpeg|gif|svg|webp|mp3|wav|m4a"
HARDCODED = re.compile(r'["`\'][^"`\']*/[^"`\']*\.(?:' + MEDIA + r')["`\']')
SLUG_LINE = re.compile(r'export\s+const\s+SLUG\s*=\s*["\']([^"\']+)["\']')

def check_src(src_dir, want_slug):
    """src/<slug>/ 의 소재 경로가 전부 asset() 을 지나는가. 반환: (검사한 파일 수, 문제 목록)"""
    files = sorted(f for f in src_dir.rglob("*.ts*") if "data" not in f.relative_to(src_dir).parts)
    bad = []
    st = src_dir/"slug.ts"
    if st.exists():
        m = SLUG_LINE.search(st.read_text(encoding="utf-8"))
        if not m:
            bad.append((st, 0, "SLUG 을 못 찾았습니다 (export const SLUG = \"…\")"))
        elif m.group(1) != want_slug:
            bad.append((st, 0, f'SLUG 이 "{m.group(1)}" 입니다 — 이 편은 "{want_slug}" 라 남의 편 소재를 가리킵니다'))
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
            if line.lstrip().startswith("//") or line.lstrip().startswith("*"): continue   # 주석의 예시는 넘어간다
            for m in HARDCODED.finditer(line):
                bad.append((f, i, f'소재 경로를 직접 적었습니다: {m.group(0)} → asset("{m.group(0).strip(chr(34)+chr(39)+chr(96)).split("/")[-1]}")'))
    return len(files), bad
pub = REMOTION_DIR/"public"/sl; data = REMOTION_DIR/"src"/sl/"data"; (pub/"nar").mkdir(parents=True, exist_ok=True); data.mkdir(parents=True, exist_ok=True)
if not p["scenes_v2"].exists(): die("scenes_v2.json 이 없습니다 — 먼저 40_nar_finalize.py 를 돌리세요.")
if not p["caps"].exists(): die("captions.json 이 없습니다 — 먼저 50_captions_build.py 를 돌리세요.")
sc = jload(p["scenes_v2"])
for s in sc["scenes"]:
    run(["ffmpeg","-v","error","-y","-i",str(ep/s["narration_file"]),"-b:a","192k",str(pub/"nar"/f"{s['id']}.mp3")])
shutil.copy(p["scenes_v2"], data/"scenes_v2.json"); jdump(jload(p["caps"]), data/"captions.json", indent=None)
print("synced", len(sc["scenes"]), "nar →", pub/"nar", "| data →", data)

# 소재가 변환본보다 나중이면 그 렌더는 옛것이다 — 남이 소재를 바꾸면 더 놓치기 쉽다.
# 화면이 깨지지 않고 **옛 그림이 멀쩡하게** 나오므로 사람 눈에 안 걸린다.
if p["visual_prep"].exists():
    vp = jload(p["visual_prep"]); stale = []
    for kind, ext in (("clips", ".mp4"), ("images", ".png")):
        for key, v in vp.get(kind, {}).items():
            fname = prep_entry(v)["src"]
            src_f, out_f = ep/"source"/fname, pub/f"{key}{ext}"
            if not src_f.exists(): continue
            if not out_f.exists():
                stale.append((key, fname, "변환본이 없습니다")); continue
            if src_f.stat().st_mtime > out_f.stat().st_mtime:
                stale.append((key, fname, f"소재가 더 새것입니다 (소재 {time.strftime('%H:%M:%S', time.localtime(src_f.stat().st_mtime))}"
                                          f" > 변환본 {time.strftime('%H:%M:%S', time.localtime(out_f.stat().st_mtime))})"))
    # 잘라낸 그림은 변환본에서 또 한 번 나온다 — 소재를 바꾸고 15 를 돌려도
    # 잘라낸 쪽이 안 따라오면 썸네일·쇼츠만 옛 그림이 된다. 사슬 두 칸을 다 본다.
    for key, c in vp.get("crops", {}).items():
        base = pub/f"{c['src']}.mp4"
        if not base.exists(): base = pub/f"{c['src']}.png"
        out_f = pub/f"{key}.png"
        if not base.exists(): continue
        if not out_f.exists():
            stale.append((key, f"{c['src']} 에서 자른 것", "잘라낸 그림이 없습니다")); continue
        if base.stat().st_mtime > out_f.stat().st_mtime:
            stale.append((key, base.name, f"변환본이 더 새것입니다 ({time.strftime('%H:%M:%S', time.localtime(base.stat().st_mtime))}"
                                         f" > 잘라낸 것 {time.strftime('%H:%M:%S', time.localtime(out_f.stat().st_mtime))})"))
    if stale:
        lines = "\n".join(f"  {k:22} {f}\n    {why}" for k, f, why in stale)
        die(f"소재가 변환본보다 나중입니다 — {len(stale)}건:\n{lines}\n"
            f"  15_clip_prep.py {a.ep} 를 먼저 돌리세요. 안 돌리면 렌더에 옛 그림이 그대로 나옵니다.", 3)
    print(f"소재 최신 검사: {sum(len(vp.get(k, {})) for k in ('clips', 'images', 'crops'))}개"
          f"(자른 것 {len(vp.get('crops', {}))}개 포함) · 뒤처진 것 0건")

# 씬 밖 구간의 클립이 실제로 있는가. 없으면 그 구간이 **검은 화면으로 멀쩡하게** 나가고 렌더는 안 죽는다.
blocks = [b for b in sc.get("blocks", []) if b.get("clip")]
if blocks:
    miss = sorted({b["clip"] for b in blocks if not (pub/f'{b["clip"]}.mp4').exists()})
    if miss:
        die(f"씬 밖 구간의 클립이 없습니다 — {len(miss)}건: {', '.join(miss)}\n"
            f"  찾은 곳: {pub}\n"
            f"  script/visual_prep.json 의 clips 에 넣고 15_clip_prep.py {a.ep} 를 돌리세요.\n"
            f"  안 돌리면 그 구간이 검은 화면으로 나가는데 렌더는 통과합니다.", 3)
    no_audio = []
    for c in sorted({b["clip"] for b in blocks}):
        r = subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=codec_name",
                            "-of","csv=p=0",str(pub/f"{c}.mp4")], capture_output=True, text=True)
        if not r.stdout.strip(): no_audio.append(c)
    if no_audio:
        die(f"씬 밖 구간의 클립에 소리가 없습니다 — {', '.join(no_audio)}\n"
            f'  15_clip_prep 은 기본이 무음입니다. visual_prep 의 그 clips 항목에 "audio": true 를 넣고 다시 돌리세요.\n'
            f"  이 구간에는 내레이션이 없습니다 — 무음으로 나가면 통째로 비어 버립니다.", 3)
    # 소리가 **있는지**만 보면 게인이 안 먹은 소재가 조용히 나간다. 실제로 인트로 클론이
    # 원본보다 4.6 dB 작은 채로 구워진 적이 있다 — 크면 「더 진짜」로 읽히는 편이라 답을 미리 준다.
    # 판정 기준은 음악 감독의 값이라 여기서는 **재서 보여만 준다.**
    lv = [(c, lufs(pub/f"{c}.mp4"), clipped(pub/f"{c}.mp4")) for c in sorted({b["clip"] for b in blocks})]
    print(f"씬 밖 구간 검사: 클립이 붙은 구간 {len(blocks)}개 · 클립 {len(lv)}종 다 있고 소리도 있습니다")
    print("  음량:", " · ".join(f"{c} {('?' if i is None else f'{i:.1f}')} LUFS 클립 {n}" for c, (i, _), n in lv))
    # 음량 차이는 **의도일 수 있다** — 이 편의 꼬리(-20.6)와 인트로(-18.0)가 2.6 LU 갈리고 그게 의도다.
    # 그래서 재서 보여만 준다. 반면 **클리핑은 언제나 사고다** — 그것만 멈춘다(음악 감독이 정한 문턱).
    # 판정은 ebur128 의 Peak 가 아니라 풀스케일 이상 샘플 수다. Peak 은 dBFS 로 반올림돼 -0.0 과 0.0 이 안 갈린다.
    # 음량은 **한 구간 안에서** 비교한다. 인트로와 꼬리처럼 떨어져 있는 구간끼리는
    # 갈리는 것이 의도다(이 편은 인트로 -18.0 · 꼬리 -20.6). 붙어 있는 것만 한 묶음으로 본다.
    groups, cur = [], []
    for b in sc.get("blocks", []):
        if cur and abs(cur[-1]["t"] + cur[-1]["sec"] - b["t"]) > 0.02:
            groups.append(cur); cur = []
        cur.append(b)
    if cur: groups.append(cur)
    li = {c: i for c, (i, _), _ in lv}
    for g in groups:
        vs = [li[b["clip"]] for b in g if b.get("clip") and li.get(b["clip"]) is not None]
        if len(vs) > 1 and max(vs) - min(vs) > 1.0:
            names = " ".join(b["clip"] for b in g if b.get("clip"))
            print(f"  ← 한 구간 안({names})에서 음량이 {max(vs) - min(vs):.1f} LU 갈립니다."
                  f" 나란히 들리는 자리라 큰 쪽이 「더 진짜」로 읽힙니다(판정은 음악 감독).")
    _clip = [(c, n) for c, _, n in lv if n > 0]
    if _clip:
        die("씬 밖 구간의 클립이 클리핑됐습니다 — " + " · ".join(f"{c} {n}샘플" for c, n in _clip) + "\n"
            "  풀스케일 이상 샘플은 의도일 수 없습니다. 소재를 다시 만들어 주세요(음악 감독).\n"
            "  게인을 먹인 소재라면 그 값이 너무 큽니다 — 15_clip_prep 은 음량을 안 건드립니다.", 3)

# 이음매 검사 — 씬과 씬 밖 구간이 프레임에서 **빈틈없이 이어 붙는가.**
# 길이를 반올림하면 앞 것의 끝과 다음 것의 시작이 한 프레임 어긋난다. 33ms 라 눈에 안 걸리고
# 렌더도 안 죽는다 — E01 v2 마스터에 실제로 틈 2곳·겹침 2곳이 있었다.
# 씬 밖 구간이 들어가면 경계가 그만큼 늘어난다(꼬리 하나에 둘).
_ep_tsx = REMOTION_DIR/"src"/"knowhow"/"Episode.tsx"
if _ep_tsx.exists():
    _src = _ep_tsx.read_text(encoding="utf-8")
    m = re.search(r"export\s+const\s+FPS\s*=\s*(\d+)", _src)
    if m and int(m.group(1)) != FPS:
        die(f"FPS 가 갈립니다 — common.py {FPS} · Episode.tsx {m.group(1)}\n"
            f"  이 값이 갈리면 아래 이음매 검사가 실제 렌더와 다른 것을 잽니다.", 3)
    # 아래 데이터 검사는 **시각표**가 맞물리는지만 본다. 실제로 틈이 났던 것은 시각표가 아니라
    # 컴포넌트가 **길이를 반올림**해서였다. 그 자리는 데이터로 못 잡으므로 코드에서 막는다.
    if re.search(r"Math\.round\(\s*\(\s*s\.t_end\s*-\s*s\.t_start\s*\)", _src):
        die("Episode.tsx 가 씬 길이를 반올림합니다 — 이음매에 한 프레임 틈이나 겹침이 생깁니다.\n"
            "  경계는 **절대 시각**으로 반올림하세요:\n"
            "    const from = Math.round(s.t_start * fps);\n"
            "    const dur  = Math.round(s.t_end * fps) - from;\n"
            "  E01 v2 마스터에 이렇게 해서 틈 2곳·겹침 2곳이 났고 24장을 다 보고도 안 걸렸습니다.\n"
            "  (Shorts.tsx 는 씬을 이어 붙이며 자기 커서를 쓰므로 해당 없습니다.)", 3)
_iv = [(round(s0["t_start"]*FPS), round(s0["t_end"]*FPS), s0["id"]) for s0 in sc["scenes"]] \
    + [(round(b["t"]*FPS), round((b["t"]+b["sec"])*FPS), f'구간@{b["t"]}s') for b in sc.get("blocks", [])]
_iv.sort()
_bad = []
for (a0, a1, an), (b0, b1, bn) in zip(_iv, _iv[1:]):
    if a1 != b0:
        _bad.append(f"  {an} 끝 {a1}f · {bn} 시작 {b0}f — {'틈 '+str(b0-a1) if b0 > a1 else '겹침 '+str(a1-b0)}프레임")
if _iv and _iv[0][0] != 0:
    _bad.insert(0, f"  편이 0f 가 아니라 {_iv[0][0]}f 에서 시작합니다 ({_iv[0][2]})")
if _bad:
    die(f"이음매가 안 맞습니다 — {len(_bad)}곳 (프레임, {FPS}fps):\n" + "\n".join(_bad) +
        "\n  그 프레임에 바탕색만 나오거나 두 장이 겹칩니다. 눈에 안 걸리고 렌더도 통과합니다.", 3)
print(f"이음매 검사: 씬 {len(sc['scenes'])}개 + 구간 {len(sc.get('blocks', []))}개 · 경계 {max(0,len(_iv)-1)}곳 · 어긋난 것 0곳")

# 소재 경로 검사. asset() 을 안 지난 경로는 남의 편을 가리켜도 tsc·remotion 이 통과시킨다.
src_dir = REMOTION_DIR/"src"/sl
tsx = [f for f in src_dir.rglob("*.ts*") if "data" not in f.relative_to(src_dir).parts] if src_dir.is_dir() else []
if a.skip_src_check:
    print("소재 경로 검사: 건너뜀 (--skip-src-check)")
elif not tsx:
    print(f"소재 경로 검사: 건너뜀 — {src_dir} 에 컴포넌트가 아직 없습니다 (remotion/README.md 의 새 에피소드 절차)")
else:
    n, bad = check_src(src_dir, sl)
    if bad:
        lines = "\n".join(f"  {f}:{i}  {msg}" if i else f"  {f}  {msg}" for f, i, msg in bad)
        die(f"소재 경로 검사 실패 — {len(bad)}건 (검사한 파일 {n}개):\n{lines}\n"
            f'  소재는 asset("파일명") 으로 씁니다 — public/{sl}/ 아래를 가리킵니다. slug 는 slug.ts 한 곳에만 둡니다.\n'
            f"  절차: remotion/README.md 의 새 에피소드 만들기", 3)
    print(f"소재 경로 검사: 파일 {n}개 · 직접 적은 경로 0건 · SLUG=\"{sl}\"")
