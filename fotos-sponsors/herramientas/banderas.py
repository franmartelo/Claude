"""Flybanners firmes: la bandera entera se pinta de un color parejo de la marca (con los
pliegues de la tela original), de borde a borde, y recién después se pega el logo.
Se engancha en rebrand.pegar: antes de pegar un logo cuyo quad cae en una bandera, la
bandera se pinta (ya sin el texto de Medifé, que borrar() sacó antes)."""
import numpy as np, cv2, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rebrand
from restos import guided

COLOR = {'ypf': (0x05, 0x4f, 0x8e), 'brahma': (0xb4, 0x0a, 0x0a), 'pepsi': (0x1d, 0x2b, 0x9c)}

# cajas (x0, y0, x1, y1) de cada flybanner en la foto original
BANDERAS = {
    'voley.jpg': [(588, 262, 862, 720), (576, 118, 630, 214)],
    'voley2.jpg': [(28, 322, 195, 720)],
    'act/voley-2.jpg': [(22, 300, 182, 667)],
    'act/voley-4.jpg': [(352, 436, 462, 634)],
    'act/tenis-5.jpg': [(28, 462, 170, 730)],
    'act/tenis-3.jpg': [(598, 120, 648, 248, 80)],
}


def silueta(O, caja):
    x0, y0, x1, y1 = caja[:4]
    smin = caja[4] if len(caja) > 4 else 135
    h = cv2.cvtColor(O, cv2.COLOR_BGR2HSV).astype(np.int16)
    # la arena también es anaranjada, pero apagada: la tela de la bandera es mucho más saturada
    nar = (((h[..., 0] <= 22) | (h[..., 0] >= 168)) & (h[..., 1] > smin) & (h[..., 2] > 60)).astype(np.uint8)
    z = np.zeros(O.shape[:2], np.uint8); z[y0:y1, x0:x1] = 1
    nar &= z
    nar = cv2.morphologyEx(nar, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    nar = cv2.morphologyEx(nar, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(nar, 8)
    if n < 2: return np.zeros(O.shape[:2], bool)
    k = 1 + np.argmax(st[1:, 4])
    m = (lab == k).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m); cv2.drawContours(out, cs, -1, 1, -1)   # rellena las letras
    # letras que tocan el borde de la bandera: claras y dentro de la envolvente
    hull = np.zeros_like(m); cv2.fillPoly(hull, [cv2.convexHull(np.vstack(cs))], 1)
    letras = (h[..., 1] < 110) & (h[..., 2] > 140) & (hull > 0)
    out = out | cv2.dilate(letras.astype(np.uint8), np.ones((3, 3), np.uint8))
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) & hull
    return (out > 0) & (z > 0)


def pintar(img, O, sil, marca):
    """img: la foto con el texto ya borrado. Devuelve la bandera pintada."""
    a = guided(O.astype(np.float32) / 255, sil.astype(np.float32), 2, 1e-3)
    a = np.clip((a - 0.1) / 0.8, 0, 1)
    a = np.maximum(a, cv2.erode(sil.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32))
    a *= cv2.dilate(sil.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    # sombreado: luminancia de la tela (sin letras), suave
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    inside = cv2.erode(sil.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    num = cv2.GaussianBlur(g * inside, (0, 0), 1.3); den = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 1.3)
    gs = num / np.maximum(den, 1e-3)
    ref = np.median(gs[inside]) if inside.any() else 128
    sh = np.clip(gs / max(ref, 1), 0.45, 1.3) ** 1.15
    col = np.array(COLOR[marca][::-1], np.float32)
    solido = np.clip(col[None, None, :] * sh[..., None], 0, 255)
    # fondo detrás del borde (cielo, arena): para que el borde no quede naranja
    fuera = (cv2.dilate(sil.astype(np.uint8), np.ones((7, 7), np.uint8)) == 0).astype(np.float32)
    nb = cv2.GaussianBlur(img.astype(np.float32) * fuera[..., None], (0, 0), 3)
    db = cv2.GaussianBlur(fuera, (0, 0), 3)[..., None]
    fondo = nb / np.maximum(db, 1e-3)
    borde = (cv2.dilate(sil.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~inside
    base = np.where(borde[..., None] & (db > 0.02), fondo, img.astype(np.float32))
    aa = a[..., None]
    out = base * (1 - aa) + solido * aa
    zona = cv2.dilate(sil.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    return np.where(zona[..., None], out, img).astype(np.uint8)


def instalar(nombre, O, marca):
    """Engancha la pintura de banderas en rebrand.pegar para esta foto."""
    sils = [silueta(O, c) for c in BANDERAS.get(nombre, [])]
    hechas = set()
    orig = rebrand._pegar_original if hasattr(rebrand, '_pegar_original') else rebrand.pegar
    rebrand._pegar_original = orig

    def pegar(img, quad, logo, cfg):
        q = np.array(quad, np.float32).mean(axis=0).astype(int)
        for i, s in enumerate(sils):
            if i not in hechas and 0 <= q[1] < s.shape[0] and 0 <= q[0] < s.shape[1] and \
               cv2.dilate(s.astype(np.uint8), np.ones((25, 25), np.uint8))[q[1], q[0]]:
                img = pintar(img, O, s, marca); hechas.add(i)
        return orig(img, quad, logo, cfg)
    rebrand.pegar = pegar
    return sils
