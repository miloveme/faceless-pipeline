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
            src_f = (CHANNEL/fname) if fname.startswith("assets/") else (ep/"source"/fname)
            out_f = pub/f"{key}{ext}"
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
_tr = sc.get("transition") or {"default": 0.0, "after": {}}
_hold = lambda i: _tr["after"].get(i, _tr["default"])
_iv = [(round(s0["t_start"]*FPS), round(s0["t_end"]*FPS), s0["id"]) for s0 in sc["scenes"]] \
    + [(round(b["t"]*FPS), round((b["t"]+b["sec"])*FPS), b.get("clip") or f'빈화면@{b["t"]}') for b in sc.get("blocks", [])]
_iv.sort()
# **`after` 의 열쇠가 실제 id 를 가리키나.** 안 맞으면 조용히 `default` 로 돌아간다 —
# 값을 지운 것과 구별이 안 되고 렌더도 통과한다. 특히 클립 없는 구간의 열쇠는
# `빈화면@9.192` 처럼 **시각이 들어 있어서**, 40 단계가 시각표를 다시 만들면 열쇠만 남고 안 맞는다.
_ids = {x[2] for x in _iv}
_orphan = [k for k in _tr.get("after", {}) if k not in _ids]
if _orphan:
    die(f"transition.after 의 열쇠 {len(_orphan)}개가 어디에도 안 맞습니다: {', '.join(_orphan)}\n"
        f"  쓸 수 있는 이름은 씬 id 와 구간 이름입니다. 지금 구간은 {len(_iv)-len(sc['scenes'])}개:\n"
        + "".join(f"    {x[2]}\n" for x in _iv if x[2] not in {y['id'] for y in sc['scenes']})
        + "  안 맞는 열쇠는 무시되고 default 로 돕니다 — 값을 지운 것과 구별이 안 됩니다.", 3)
# 전환이 있으면 경계는 **한 점이 아니라 구간**이다. 앞 것이 전환 길이만큼 더 남아 있어야 한다 —
# 덜 남으면 그 사이에 바탕만 나오고, 더 남으면 다음 것이 늦게 덮인다. 둘 다 렌더는 안 죽는다.
_bad = []
for (a0, a1, an), (b0, b1, bn) in zip(_iv, _iv[1:]):
    if a1 != b0:
        _bad.append(f"  {an} 끝 {a1}f · {bn} 시작 {b0}f — {'틈 '+str(b0-a1) if b0 > a1 else '겹침 '+str(a1-b0)}프레임")
if _iv and _iv[0][0] != 0:
    _bad.insert(0, f"  편이 0f 가 아니라 {_iv[0][0]}f 에서 시작합니다 ({_iv[0][2]})")
if _bad:
    die(f"이음매가 안 맞습니다 — {len(_bad)}곳 (프레임, {FPS}fps):\n" + "\n".join(_bad) +
        "\n  그 프레임에 바탕색만 나오거나 두 장이 겹칩니다. 눈에 안 걸리고 렌더도 통과합니다.", 3)
_ov = sum(1 for (_, _, an), _ in zip(_iv, _iv[1:]) if _hold(an) > 0)
print(f"이음매 검사: 씬 {len(sc['scenes'])}개 + 구간 {len(sc.get('blocks', []))}개 · 경계 {max(0,len(_iv)-1)}곳 · 어긋난 것 0곳"
      + (f" · 전환이 붙는 경계 {_ov}곳(앞 것이 그만큼 더 남는다)" if _ov else ""))

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

    # 이름이 실제로 있는가. **asset() 을 지나도 파일 이름이 틀리면 렌더는 안 죽는다** —
    # 그 프레임에서 404 가 나고 그 씬만 검게 빈다. E01 에서 실제로 여섯 개가 .jpg 로 적혀 있었고
    # (15_clip_prep 은 그림을 전부 png 로 만든다) 그 씬을 렌더해 보기 전에는 아무 데서도 안 걸렸다.
    _lit, _dyn = set(), 0
    for _f in tsx:
        for _line in _f.read_text(encoding="utf-8").split("\n"):
            _t = _line.lstrip()
            if _t.startswith("//") or _t.startswith("*") or _t.startswith("/*"): continue
            _lit |= set(re.findall(r'asset\(\s*"([^"]+)"\s*\)', _line))
            _dyn += len(re.findall(r"asset\(\s*[`$a-zA-Z_]", _line))
    _gone = sorted(x for x in _lit if not (pub/x).exists())
    if _gone:
        _have = sorted(p.name for p in pub.iterdir() if p.is_file())
        die(f"소재 이름이 public/{sl}/ 에 없습니다 — {len(_gone)}개:\n"
            + "\n".join(f"  {x}" for x in _gone)
            + f"\n  있는 것 {len(_have)}개: " + " ".join(_have[:24]) + (" …" if len(_have) > 24 else "")
            + "\n  15_clip_prep 은 그림을 전부 .png 로 만듭니다. 확장자를 먼저 보세요.\n"
              "  이름이 틀려도 렌더는 안 죽습니다 — 그 씬만 검게 빕니다.", 3)
    print(f"소재 이름 검사: 이름으로 적은 것 {len(_lit)}개 다 있습니다"
          + (f" · 조립해서 부르는 자리 {_dyn}곳은 못 봅니다(그 씬을 스틸로 확인하세요)" if _dyn else ""))

_copy = src_dir/"copy.ts"          # 화면 문구 파일. 아래 검사 셋이 같이 본다

# 화면에 나가면 안 되는 글자. **낱말 목록으로는 못 막는다** — 실제로 금지 목록에
# URL·계정 주소·작업 시각만 있어서 `ref/source.mp4`(원본 드라마 파일 이름)가 s27 화면에 떴다.
# 그래서 **모양**으로 잡는다.
#   경로 조각   슬래시가 든 문자열. 파일 이름 자체는 화면에 쓰는 자리가 있지만(s21 의 폐기본 이름들)
#               **경로는 없다** — 우리 작업 폴더 구조와 원본 파일을 드러낸다
#   없는 글자   ✗(U+2717) 은 Apple SD Gothic Neo 에 없어 두부(□)로 나온다. 렌더는 통과한다.
#               한 쌍 중 하나만 있으면 짝이 깨지므로 이 편은 ✓ 도 안 쓴다(미술).
_STR = re.compile(r'"((?:[^"\\]|\\.)*)"')
_PATH = re.compile(r'(?:^|[\s(\[])(?:ref|out|assets|analysis|stills|reedit|DC|src|public)/|/Users|/private/tmp|~/|https?://')
# **목록이다. 서체를 여기서 열어 볼 수 없어서** — 폰트는 렌더할 때 브라우저가 받는다.
# 그래서 「없다고 확인된 것」만 막는다. 화살표(→ U+2192)처럼 이미 쓰고 있고 잘 나오는 것은 안 막는다.
# 새로 걸리는 글자가 나오면 여기 더한다.
_GLYPH = re.compile(r'[\u2713\u2714\u2715\u2716\u2717\u2718\u2611\u2612\u274c\u2705]')
if src_dir.is_dir():
    _bad = []
    for _f in tsx:
        for _i, _line in enumerate(_f.read_text(encoding="utf-8").split("\n"), 1):
            _t = _line.lstrip()
            if _t.startswith(("//", "*", "/*")): continue          # 주석은 화면에 안 나간다
            _clean = re.sub(r'asset\(\s*"[^"]*"\s*\)', "asset()", _line)   # 소재 경로는 이 검사 대상이 아니다
            for _m in _STR.finditer(_clean):
                _v = _m.group(1)
                if _PATH.search(_v): _bad.append((_f.name, _i, "경로 조각", _v))
                for _g in set(_GLYPH.findall(_v)):
                    _bad.append((_f.name, _i, f"서체에 없을 수 있는 글자 U+{ord(_g):04X}", _v))
    if _bad:
        die(f"화면에 나가면 안 되는 글자가 있습니다 — {len(_bad)}건:\n"
            + "\n".join(f"  {a}:{b}  {c}  {d[:70]}" for a, b, c, d in _bad)
            + "\n  경로는 우리 작업 폴더와 원본 파일을 드러냅니다. 파일 **이름**을 화면에 쓰는 자리는 있어도\n"
              "  **경로**를 쓰는 자리는 없습니다(연출). 소재는 asset() 으로 부르므로 이 검사에 안 걸립니다.\n"
              "  기호는 서체에 없으면 두부(□)가 되는데 렌더는 통과합니다 — 판정은 낱말로 하세요.", 3)
    print(f"화면 글자 검사: 파일 {len(tsx)}개 · 경로 조각 0건 · 서체에 없는 기호 0건")

# 화면 문구가 자막을 받아쓰나 — **겹말 검사**(연출 요청).
# 목소리·자막·큰 글자가 같은 말을 세 번 하면 화면이 자막의 메아리가 된다.
# 이 편에서 사람 눈으로 여섯 번 놓쳤다(s16 「사람이 하는 0.7초」· s21 결론 세 줄 · s25 판정 줄 …).
#
# **막지 않고 세어 보여준다.** 짧게 겹치는 것은 정상이고(「원본」·숫자·「AI 클론」),
# 어디까지가 겹말인지는 연출이 보고 정할 일이다. 기계는 **후보를 좁혀 주는 데까지** 한다.
# 걸리는 선은 둘을 같이 본다 — **이어서 5자 이상이면서 그 문구의 절반 이상**.
#   s16 「사람 0.7초」  vs 자막 「사람이 하는 0.7초에…」  가장 긴 연속 4자 → 안 걸림(고친 뒤)
#   s16 「사람이 하는 0.7초」(고치기 전)                  9자 · 100% → 걸림
# 씬은 copy.ts 의 `export const S<NN>` 덩어리로 가른다 — 박자 시각은 여기 없으므로 씬 단위로만 댄다.
def _flat(t): return re.sub(r"[\s.,·「」()·—:/]", "", t)
def _run(a, b):
    """a 안에서 b 와 이어서 겹치는 가장 긴 토막의 길이"""
    best = 0
    for i in range(len(a)):
        for j in range(i + best + 1, len(a) + 1):
            if a[i:j] in b: best = j - i
            else: break
    return best
_caps_p = p["caps"]
if _copy.exists() and _caps_p.exists():
    _caps = jload(_caps_p)
    _txt = _copy.read_text(encoding="utf-8")
    _parts = re.split(r"^export const S(\d\d)", _txt, flags=re.M)
    _echo = []
    for _k in range(1, len(_parts), 2):
        _sid = "s" + _parts[_k]
        _cap = _flat("".join(c["text"] for c in _caps.get(_sid, [])))
        if not _cap: continue
        for _m in re.finditer(r'"((?:[^"\\]|\\.)*)"', _parts[_k + 1]):
            _v = _m.group(1)
            if len(_flat(_v)) < 5: continue
            _n = _run(_flat(_v), _cap)
            if _n >= 5 and _n >= len(_flat(_v)) * 0.5:
                _echo.append((_sid, _n, len(_flat(_v)), _v))
    if _echo:
        print(f"겹말 후보: {len(_echo)}건 — 화면 문구가 그 씬 자막을 받아씁니다 (막지 않습니다. 판단은 연출)")
        for _sid, _n, _l, _v in sorted(_echo, key=lambda x: -x[1]):
            print(f"  {_sid}  이어서 {_n}자 / 문구 {_l}자  「{_v[:44]}{'…' if len(_v) > 44 else ''}」")
    else:
        print("겹말 검사: 화면 문구가 자막을 받아쓰는 자리 0건 (이어서 5자 이상 · 문구의 절반 이상)")

# 참조가 끊긴 소재 — visual_prep 에 있는데 **어느 씬도 안 부르는** 항목(음악 감독 요청).
# 씬이 바뀌어 안 쓰게 돼도 항목은 남고 15 는 계속 굽는다. 렌더에 안 나가니 해롭지는 않지만
# 「이건 왜 있지」가 다음 편까지 간다.
#
# **막지 않고 센다.** 지금 안 쓰여도 다음 편에 쓸 수 있고 **그 판단은 항목 주인(연출·미술)이 한다.**
# 검사는 「이건 지금 안 쓰인다」까지만 말한다. 그리고 **조립해서 부르는 자리는 못 본다** — 그 수를 같이 찍는다.
if p["visual_prep"].exists() and src_dir.is_dir():
    _vp = jload(p["visual_prep"])
    _keys = {k for sec in ("clips", "images", "stills", "crops")
             for k in _vp.get(sec, {}) if k != "_"}
    _used, _dyn2 = set(), 0
    for _f in tsx:
        for _line in _f.read_text(encoding="utf-8").split("\n"):
            _t = _line.lstrip()
            if _t.startswith(("//", "*", "/*")): continue
            for _m in re.findall(r'asset\(\s*"([^"]+)"\s*\)', _line):
                _used.add(_m.rsplit(".", 1)[0])
            for _m in re.findall(r'"([A-Za-z0-9_]+)\.(?:mp4|png|jpg)"', _line):
                _used.add(_m)                      # 배열에 담아 asset(f) 로 부르는 자리
            _dyn2 += len(re.findall(r"asset\(\s*[`$]", _line))
    # **씬만 보면 안 된다.** 씬 밖 구간은 Episode.tsx 가 blocks 의 clip 이름으로 직접 부르고,
    # crops 는 그 원본 클립을 물고 있다. 그것을 안 세면 인트로·꼬리가 「안 쓰는 것」으로 나온다.
    _used |= {b["clip"] for b in sc.get("blocks", []) if b.get("clip")}
    _used |= {v["src"] for v in _vp.get("crops", {}).values() if isinstance(v, dict) and v.get("src")}
    # **지우지 않고 「안 씀」이라고 적는 자리를 둔다**(미술). 목록에서 빼면 점검 대상에서도 사라진다 —
    # 이 편에서 `s00_orig_still.png` 이 목록 밖이라 아무도 안 봤고 덧칠본이 화면에 올라갔다.
    # visual_prep 에 top-level `"unused": ["arc12", …]` 을 두면 그쪽으로 세고 목록에서 뺀다.
    _marked = set(_vp.get("unused", []))
    _idle = sorted(k for k in _keys if k not in _used and k not in _marked)
    _stale = sorted(k for k in _marked if k in _used)          # 「안 씀」이라 적었는데 씬이 부른다
    print(f"소재 쓰임 검사: visual_prep 항목 {len(_keys)}개 · 씬이 부르는 것 {len(_keys - set(_idle) - _marked)}개"
          + (f" · 「안 씀」이라 적힌 것 {len(_marked)}개" if _marked else "")
          + (f" · **적혀 있지 않은데 안 부르는 것 {len(_idle)}개**" if _idle else " · 안 적힌 것 0개")
          + (f" · 조립해서 부르는 자리 {_dyn2}곳은 못 봅니다" if _dyn2 else ""))
    if _idle:
        print("  " + " · ".join(_idle))
        print('  지울지는 항목 주인(연출·미술)이 정합니다. 막지 않습니다.')
        print('  남겨 둘 것이면 visual_prep 에 "unused": [...] 로 적어 주세요 — 그러면 여기서 빠집니다.')
    if _stale:
        print(f"  ← 「안 씀」이라 적혀 있는데 씬이 부르는 것 {len(_stale)}개: " + " · ".join(_stale))
    # 목록에서 이름을 바꾸면 **옛 이름으로 구운 파일이 public 에 그대로 남는다.**
    # 코드가 옛 이름을 부르면 조용히 그 파일이 나간다 — 「소재 이름 검사」는 있는 파일만 보므로 못 잡는다.
    # 스틸은 `<키>_<초>.png` 로 여러 장이 나온다. 키만 대면 그 전부가 고아로 잡힌다
    _made = set(_keys) | {f"{k}_{t}" for k, ts in _vp.get("stills", {}).items()
                          if k != "_" for t in ts}
    _orphan = sorted(x.stem for x in pub.iterdir()
                     if x.is_file() and x.suffix in (".png", ".mp4") and x.stem not in _made)
    if _orphan:
        print(f"  ← visual_prep 에 없는데 public 에 구워져 있는 것 {len(_orphan)}개: " + " · ".join(_orphan))
        print("     이름을 바꾸면 옛 파일이 남습니다. 코드가 옛 이름을 부르면 조용히 그게 나갑니다.")

# 안 정해진 문구 검사 — copy.ts 의 `null` 은 **아직 담당이 정하지 않은 값**이다.
# 화면에는 빨간 「연출 대기」 상자로 뜨지만 그것만으로는 못 막는다. 렌더는 통과하고
# 마스터에 그대로 실려 나간다. 임시 낱말을 안 넣기로 한 규칙이 값을 하려면 여기서 세어야 한다.
if _copy.exists():
    _wait = re.findall(r"^\s*(\w+)Wait:\s*\"([^\"]*)\"", _copy.read_text(encoding="utf-8"), re.M)
    _null = set(re.findall(r"^\s*(\w+):\s*null\s+as\s+Pend<", _copy.read_text(encoding="utf-8"), re.M))
    _open = [(k, w) for k, w in _wait if k in _null]
    if _open:
        die(f"화면 문구가 아직 안 정해졌습니다 — {len(_open)}자리 ({_copy.name}):\n"
            + "\n".join(f"  {k}: {w}" for k, w in _open)
            + "\n  연출 감독이 정할 값입니다. 화면에는 빨간 「연출 대기」 상자로 떠 있습니다.\n"
              "  임시 낱말을 넣지 마세요 — 한 번 넣으면 그대로 남습니다.", 3)
    print(f"화면 문구 검사: {_copy.name} · 기다리는 자리 0곳")
