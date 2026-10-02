"""Versión final de cada foto (1x): ropa puesta = original naranja con el logo de la marca;
objetos (colchonetas, bolsas, mantas, carteles, libros) = teñidos; flybanners = sólidos.
  L: orig/logo/<marca>/<foto>.png  (sin teñir, logos pegados, banderas sólidas)
  T: corr/<marca>/<foto>.png       (teñido corregido; Pepsi con el azul ajustado)
"""
import cv2, numpy as np, sys, os
sys.path.insert(0, '.'); sys.path.insert(0, 'orig')
from restos import clases, guided, retoques
import ajustes
from pepsi_fix import azul_creible
import banderas

# por foto: 'L' = todo sin teñir; 'T' = todo teñido; si no, mezcla automática
ELECCION = {
    'act/eventos-3.jpg': 'T',  # la bolsa: entera del color de la marca
    'act/staff-5.jpg': 'L',    # remera naranja; la mezcla dejaba parches
    'act/eventos-4.jpg': 'T',  # la manta del público: entera del color de la marca
    # vóley: gente chica y lejos (MediaPipe no siempre la detecta); las banderas ya son sólidas en L
    'voley.jpg': 'L', 'voley2.jpg': 'L', 'act/voley-1.jpg': 'L', 'act/voley-2.jpg': 'L',
    'act/voley-3.jpg': 'L', 'act/voley-4.jpg': 'L', 'act/tenis-5.jpg': 'L', 'act/tenis-3.jpg': 'L',
    'act/padel-6.jpg': 'L',   # las bolsas las tienen en la mano: quedan naranjas con el logo, como las pecheras
}


def textos_viejos(R, O, cl, P):
    """Borra letras claras de Medifé que quedaron intactas sobre tela naranja (cintas, remeras):
    claras, sin cambios respecto del original, rodeadas de naranja, sobre ropa."""
    esc = O.shape[1] / 1000
    h = cv2.cvtColor(R, cv2.COLOR_BGR2HSV).astype(np.int16)
    nar = (((h[..., 0] <= 25) | (h[..., 0] >= 170)) & (h[..., 1] > 110)).astype(np.float32)
    L = cv2.cvtColor(R, cv2.COLOR_BGR2Lab)[..., 0].astype(np.float32)
    med = cv2.medianBlur(L.astype(np.uint8), max(int(15 * esc) | 1, 7)).astype(np.float32)
    claro = (h[..., 1] < 145) & (h[..., 2] > 140) & ((L - med) > 12)
    igual = np.abs(R.astype(np.int16) - O.astype(np.int16)).max(2) < 20
    # nunca cerca de un logo pegado: donde la foto cambió de verdad (no teñido), con margen
    hO = cv2.cvtColor(O, cv2.COLOR_BGR2HSV).astype(np.int16)
    cambio = np.abs(R.astype(np.int16) - O.astype(np.int16)).max(2) > 40
    pegado = cambio & ~((((h[..., 0] >= 95) & (h[..., 0] <= 135)) | (h[..., 0] <= 8) | (h[..., 0] >= 170)) & (h[..., 1] > 120) & (((hO[..., 0] <= 25) | (hO[..., 0] >= 170)) & (hO[..., 1] > 110)))
    pegado = cv2.morphologyEx(pegado.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    igual &= cv2.dilate(pegado, np.ones((max(int(31 * esc) | 1, 15),) * 2, np.uint8)) == 0
    rodeado = cv2.blur(nar, (9, 9)) > 0.4
    ropa = cv2.dilate(np.isin(cl, [4, 5]).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    cand = claro & igual & rodeado & ropa
    if P.get('sin_textos'):
        cand[:] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), 8)
    ok = (st[:, 4] >= 3) & (st[:, 4] <= 400 * esc * esc); ok[0] = False
    cand = ok[lab]
    if not cand.any(): return R
    le = cv2.dilate(cand.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2) > 0
    valid = ((nar > 0) & ~le).astype(np.float32)
    num = cv2.GaussianBlur(R.astype(np.float32) * valid[..., None], (0, 0), 3)
    den = cv2.GaussianBlur(valid, (0, 0), 3)[..., None]
    fill = num / np.maximum(den, 1e-3)
    ruido = np.random.default_rng(3).normal(0, 1.6, R.shape[:2])[..., None]
    ml = cv2.GaussianBlur(le.astype(np.float32), (0, 0), 0.7)[..., None] * (den > 0.05)
    return np.clip(R * (1 - ml) + (fill + ruido) * ml, 0, 255).astype(np.uint8)


def componer(m, k, O, cl=None):
    R = _componer(m, k, O, cl)
    if cl is None: cl = clases(O)
    P = dict(ajustes.AJUSTES.get(k, {})); P.update(ajustes.AJUSTES.get(f'{m}:{k}', {}))
    R = textos_viejos(R, O, cl, P)
    return retoques(O, R, P)


def _componer(m, k, O, cl=None):
    L = cv2.imread(f'orig/logo/{m}/{k[:-4]}.png')
    T = cv2.imread(f'corr/{m}/assets/img/{k[:-4]}.png')
    if m == 'pepsi': T = azul_creible(T, O)
    modo = ELECCION.get(f'{m}:{k}', ELECCION.get(k))
    if modo == 'L' or T is None: return L
    if modo == 'T': return T
    if cl is None: cl = clases(O)
    persona = cv2.dilate(np.isin(cl, [1, 2, 3, 4, 5]).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    flags = np.zeros(O.shape[:2], bool)
    for c in banderas.BANDERAS.get(k, []):
        flags |= cv2.dilate(banderas.silueta(O, c).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    dif = np.abs(T.astype(np.int16) - O.astype(np.int16)).max(2)
    obj = (dif > 25) & ~persona & ~flags
    obj = cv2.morphologyEx(obj.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(obj, 8)
    ok = st[:, 4] >= 40; ok[0] = False
    obj = ok[lab]
    a = guided(O.astype(np.float32) / 255, obj.astype(np.float32), 2, 1e-3)
    a = np.clip((a - 0.1) / 0.8, 0, 1) * (cv2.dilate(obj.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) * ~persona
    # bordes del objeto (colchonetas): todo lo naranja pegado al objeto también va
    hO = cv2.cvtColor(O, cv2.COLOR_BGR2HSV).astype(np.int16)
    naranja = ((hO[..., 0] <= 25) | (hO[..., 0] >= 170)) & (hO[..., 1] > 70)
    borde = (cv2.dilate(obj.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & naranja & ~persona & (dif > 8)
    a = np.maximum(a, cv2.GaussianBlur(borde.astype(np.float32), (0, 0), 0.7))
    a = a[..., None]
    return np.clip(L * (1 - a) + T * a, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    marcas = [x for x in sys.argv[1:] if x in ('ypf', 'brahma', 'pepsi')] or ['ypf', 'brahma', 'pepsi']
    solo = [x for x in sys.argv[1:] if x not in marcas]
    fs = [f.replace('assets/img/', '') for f in open('web/diff.txt').read().split() if f.endswith('.jpg')]
    for k in fs:
        if solo and k not in solo: continue
        O = cv2.imread('web/orig/assets/img/' + k); cl = clases(O)
        for m in marcas:
            R = componer(m, k, O, cl)
            o = f'elegida/{m}/assets/img/{k[:-4]}.png'; os.makedirs(os.path.dirname(o), exist_ok=True)
            cv2.imwrite(o, R)
        print('ok', k, flush=True)
