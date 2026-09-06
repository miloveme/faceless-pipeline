"""화자 유사도 비교 (librosa). 참조 음성 대 생성 결과.
음색 = MFCC 20차 평균 코사인 / 변동폭 = MFCC 표준편차 상대거리 / 음높이 = f0 중앙값"""
import sys, numpy as np, librosa

def feat(f):
    y, sr = librosa.load(f, sr=16000, mono=True)
    y, _ = librosa.effects.trim(y, top_db=30)
    m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)[1:]      # 0차(에너지) 제외
    f0 = librosa.yin(y, fmin=60, fmax=400, sr=sr)
    f0 = f0[(f0 > 60) & (f0 < 400)]
    return m.mean(1), m.std(1), (float(np.median(f0)) if len(f0) else float('nan')), len(y)/sr

cos = lambda a, b: float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
ref, gens = sys.argv[1], sys.argv[2:]
rm, rs, rf, rd = feat(ref)
print(f"{'파일':<24}{'음색 유사도':>12}{'변동폭 차이':>12}{'음높이':>10}{'차이':>7}{'길이':>8}")
print(f"{ref.split('/')[-1]:<24}{'기준':>12}{'':>12}{rf:>8.0f}Hz{'':>7}{rd:>7.1f}s")
for g in gens:
    gm, gs, gf, gd = feat(g)
    print(f"{g.split('/')[-1]:<24}{cos(rm,gm):>12.4f}{np.linalg.norm(rs-gs)/np.linalg.norm(rs):>12.3f}{gf:>8.0f}Hz{gf-rf:>+6.0f}{gd:>8.1f}s")
