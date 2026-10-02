"""Ajustes finales solo para Pepsi, sobre las fotos ya terminadas (2x).
  1. Azul más creíble: la tela teñida pasa de un azul violáceo plano a un azul Pepsi
     con un poco menos de saturación y los pliegues de la tela más marcados.
  2. Flybanners firmes: dentro de cada bandera (polígonos a mano), color parejo de
     borde a borde, sin manchas ni bordes naranjas; el logo queda.
  3. Camperas naranjas: vuelven al naranja original; solo se deja el logo de Pepsi.
"""
import cv2, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restos import clases, _poly

H_DEST = 115      # tono OpenCV: ~230°, azul Pepsi menos violáceo (antes 120)
S_K = 0.88        # saturación relativa
CONTRASTE = 1.3   # pliegues

BANDERAS = {   # coords de la foto web original (1x)
}
CAMPERAS = ['staff.jpg', 'staff2.jpg', 'act/staff-1.jpg', 'act/staff-2.jpg', 'act/staff-3.jpg']


def tela_mask(res, Ou):
    h = cv2.cvtColor(res, cv2.COLOR_BGR2HSV).astype(np.int16)
    ho = cv2.cvtColor(Ou, cv2.COLOR_BGR2HSV).astype(np.int16)
    azul = (h[..., 0] >= 112) & (h[..., 0] <= 138) & (h[..., 1] > 70)
    era_nar = ((ho[..., 0] <= 26) | (ho[..., 0] >= 170)) & (ho[..., 1] > 40)
    m = (azul & era_nar).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 1.0)


def azul_creible(res, Ou):
    m = tela_mask(res, Ou)
    hsv = cv2.cvtColor(res, cv2.COLOR_BGR2HSV).astype(np.float32)
    lab = cv2.cvtColor(res, cv2.COLOR_BGR2Lab).astype(np.float32)
    L = lab[..., 0]
    media = cv2.GaussianBlur(L, (0, 0), 25)
    L2 = np.clip(media + (L - media) * CONTRASTE, 0, 255)
    hsv2 = hsv.copy()
    hsv2[..., 0] = H_DEST + (hsv[..., 0] - 120) * 0.5
    hsv2[..., 1] = hsv[..., 1] * S_K
    out = cv2.cvtColor(np.clip(hsv2, 0, [179, 255, 255]).astype(np.uint8), cv2.COLOR_HSV2BGR)
    lab2 = cv2.cvtColor(out, cv2.COLOR_BGR2Lab).astype(np.float32)
    lab2[..., 0] = L2
    out = cv2.cvtColor(np.clip(lab2, 0, 255).astype(np.uint8), cv2.COLOR_Lab2BGR).astype(np.float32)
    mm = m[..., None]
    return np.clip(res * (1 - mm) + out * mm, 0, 255).astype(np.uint8)


def camperas_naranjas(res, O, Ou):
    cl = clases(O)
    ropa = (cl == 4).astype(np.uint8)
    ho = cv2.cvtColor(O, cv2.COLOR_BGR2HSV).astype(np.int16)
    nar = (((ho[..., 0] <= 26) | (ho[..., 0] >= 170)) & (ho[..., 1] > 40)).astype(np.uint8)
    camp = cv2.morphologyEx(ropa & nar, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    camp = cv2.resize(camp.astype(np.float32), (res.shape[1], res.shape[0]))
    # logo de Pepsi en la versión teñida: blanco/rojo/azul que no es tela
    h = cv2.cvtColor(res, cv2.COLOR_BGR2HSV).astype(np.int16)
    tela = (h[..., 0] >= 105) & (h[..., 0] <= 140) & (h[..., 1] > 70) & (h[..., 2] < 230)
    logo = (camp > 0.5) & ~tela
    hu = cv2.cvtColor(Ou, cv2.COLOR_BGR2HSV).astype(np.int16)
    logo &= ~((((hu[..., 0] <= 26) | (hu[..., 0] >= 170)) & (hu[..., 1] > 40)) & ~((h[..., 1] < 60) | (h[..., 0] < 8) | (h[..., 0] > 165)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(logo.astype(np.uint8), 8)
    # el logo es una pastilla compacta; descartar hilitos sueltos
    ok = (st[:, 4] > 60) & (st[:, 2] < res.shape[1] * 0.1) & (st[:, 3] < res.shape[0] * 0.1); ok[0] = False
    logo = ok[lab]
    logo = cv2.morphologyEx(logo.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    logo = cv2.dilate(logo, np.ones((3, 3), np.uint8))
    # textos viejos claros sobre la campera original: se rellenan con el naranja de alrededor
    Lu = cv2.cvtColor(Ou, cv2.COLOR_BGR2Lab)[..., 0].astype(np.float32)
    med = cv2.medianBlur(Lu.astype(np.uint8), 31).astype(np.float32)
    texto = (camp > 0.5) & ((Lu - med) > 14) & (hu[..., 1] < 150)
    texto = cv2.dilate(texto.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    valid = ((camp > 0.5) & ~texto).astype(np.float32)
    num = cv2.GaussianBlur(Ou.astype(np.float32) * valid[..., None], (0, 0), 6)
    den = cv2.GaussianBlur(valid, (0, 0), 6)[..., None]
    fill = num / np.maximum(den, 1e-3)
    base = np.where(texto[..., None], fill, Ou.astype(np.float32))
    mc = cv2.GaussianBlur(np.clip(camp, 0, 1), (0, 0), 1.2)[..., None]
    ml = cv2.GaussianBlur(logo.astype(np.float32), (0, 0), 0.8)[..., None]
    out = res * (1 - mc) + base * mc
    out = out * (1 - ml) + res * ml
    return np.clip(out, 0, 255).astype(np.uint8)


def banderas(res, Ou, polys):
    k = res.shape[1] / Ou.shape[1] if False else 1
    z = _poly(res.shape, [[(x * 2, y * 2) for x, y in p] for p in polys])
    h = cv2.cvtColor(res, cv2.COLOR_BGR2HSV).astype(np.int16)
    logo = z & ((h[..., 1] < 90) | (h[..., 0] < 10) | (h[..., 0] > 160)) & ~((h[..., 0] <= 26) & (h[..., 1] > 90))
    logo = cv2.morphologyEx(logo.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(logo, 8)
    ok = st[:, 4] > 400; ok[0] = False
    logo = cv2.dilate(ok[lab].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    tela = z & ~logo
    # color de la bandera: mediana de su tela azul
    azul = tela & (h[..., 0] >= 100) & (h[..., 0] <= 125) & (h[..., 1] > 80)
    col = np.median(res[azul], axis=0) if azul.sum() > 50 else np.array([170, 60, 20])
    # sombreado suave de la tela original (pliegues grandes), sin manchas
    L = cv2.cvtColor(Ou, cv2.COLOR_BGR2GRAY).astype(np.float32)
    Ls = cv2.GaussianBlur(L, (0, 0), 6)
    ref = np.median(Ls[tela]) if tela.any() else 128
    sh = np.clip(1 + (Ls / max(ref, 1) - 1) * 0.6, 0.7, 1.25)[..., None]
    plano = np.clip(col[None, None, :] * sh, 0, 255)
    mt = cv2.GaussianBlur(tela.astype(np.float32), (0, 0), 1.0)[..., None]
    return np.clip(res * (1 - mt) + plano * mt, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    fs = [f for f in open('web/diff.txt').read().split() if f.endswith('.jpg')]
    solo = sys.argv[3:]
    for f in fs:
        k = f.replace('assets/img/', '')
        if solo and k not in solo: continue
        res = cv2.imread(f'{src}/{f}'); O = cv2.imread(f'web/orig/{f}')
        Ou = cv2.resize(O, (res.shape[1], res.shape[0]), interpolation=cv2.INTER_LANCZOS4)
        res = azul_creible(res, Ou)
        if k in BANDERAS: res = banderas(res, Ou, BANDERAS[k])
        if k in CAMPERAS: res = camperas_naranjas(res, O, Ou)
        o = f'{dst}/{f}'; os.makedirs(os.path.dirname(o), exist_ok=True)
        cv2.imwrite(o, res, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1, cv2.IMWRITE_JPEG_OPTIMIZE, 1])
        print('ok', k, flush=True)
