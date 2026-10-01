"""Corrige (si hace falta), amplía x2 con Real-ESRGAN y termina cada foto para la web."""
import sys, os, cv2, numpy as np, time
sys.path.insert(0, '.')
from sr import sr2

from terminar2 import terminar as terminar_nuevo


def terminar_viejo(sr, base):
    # 80% IA + 20% ampliación clásica: conserva algo de la textura original y evita el look "plástico"
    up = cv2.resize(base, (sr.shape[1], sr.shape[0]), interpolation=cv2.INTER_LANCZOS4)
    out = sr.astype(np.float32) * 0.8 + up.astype(np.float32) * 0.2
    # grano fino de foto, más suave en zonas claras
    g = np.random.default_rng(7).normal(0, 1.6, sr.shape[:2]).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.6)[..., None]
    L = out.mean(2, keepdims=True) / 255
    out = out + g * (1.2 - 0.6 * L)
    return np.clip(out, 0, 255).astype(np.uint8)

todas = [f for f in open('web/ypf/list.txt').read().split() if f.endswith('.jpg')]
dif = set(open('web/diff.txt').read().split())
for m in (sys.argv[1:] or ['ypf', 'brahma', 'pepsi']):
    for f in todas:
        o = f'out/{m}/{f}'
        if os.path.exists(o): continue
        t = time.time()
        # la ampliación cruda se guarda en caché, así retocar la terminación no obliga a rehacerla
        src = f'corr/{m}/{f[:-4]}.png' if f in dif else f'web/orig/{f}'
        base = cv2.imread(src)
        c = f'sr_cache/{m}/{f[:-4]}.png' if f in dif else f'sr_cache/comun/{f[:-4]}.png'
        if not os.path.exists(c) and f not in dif and os.path.exists(f'sr_out/comun/{f}'):
            os.makedirs(os.path.dirname(c), exist_ok=True)
            cv2.imwrite(c, cv2.imread(f'sr_out/comun/{f}'))
        if os.path.exists(c) and os.path.getmtime(c) >= os.path.getmtime(src):
            sr = cv2.imread(c)
        else:
            sr = sr2(base)
            os.makedirs(os.path.dirname(c), exist_ok=True)
            cv2.imwrite(c, sr)
        res = terminar_nuevo(sr, base, fuerza=0.3 if 'padel' in f else 0.85)  # alambrados: la IA inventa texturas
        os.makedirs(os.path.dirname(o), exist_ok=True)
        cv2.imwrite(o + '.tmp.jpg', res, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1, cv2.IMWRITE_JPEG_OPTIMIZE, 1])
        os.replace(o + '.tmp.jpg', o)
        print(m, f, '%.0fs' % (time.time() - t), flush=True)
    print(m, 'LISTO', flush=True)
