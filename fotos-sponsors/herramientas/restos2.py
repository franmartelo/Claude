"""Corrige el re-branding de Medifé en una foto ya pasada a otra marca.

Compara el original (O) con la versión de la marca (B):
  1. Prendas: MediaPipe marca la ropa; toda prenda naranja que la versión de la
     marca ya había teñido en parte se vuelve a teñir entera desde el original,
     con un color parejo (sin parches ni costados naranjas).
  2. Objetos (colchonetas, banderas, redes): se completa el teñido de los bordes
     naranjas pegados a lo ya teñido, siguiendo el borde real (guided filter).
  3. Retoques a mano por foto (ajustes.py): restaurar zonas, borrar textos.
Los logos que puso la versión de la marca se respetan.
"""
import numpy as np, cv2
from restos import clases, guided, _poly, retoques


def _hsv(img):
    h = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return h[..., 0].astype(np.int16), h[..., 1].astype(np.int16), h[..., 2].astype(np.int16)


def mapa_color(O, B, t):
    """Aprende cómo pasó el naranja del original al color de la marca (en Lab)."""
    LO = cv2.cvtColor(O.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
    LB = cv2.cvtColor(B.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
    lo, lb = LO[..., 0][t], LB[..., 0][t]
    coef = np.polyfit(lo, lb, 2) if np.ptp(lo) > 20 else np.polyfit(lo, lb, 1)
    cO = np.hypot(LO[..., 1], LO[..., 2])
    k = float(np.median(np.hypot(LB[..., 1][t], LB[..., 2][t]) / np.maximum(cO[t], 1)))
    ang = float(np.arctan2(np.median(LB[..., 2][t]), np.median(LB[..., 1][t])))
    lmin, lmax = np.percentile(lb, 0.5), np.percentile(lb, 99.5)

    def aplicar(img):
        L = cv2.cvtColor(img.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
        nL = np.clip(np.polyval(coef, L[..., 0]), max(lmin - 8, 1), min(lmax + 8, 99))
        nC = np.hypot(L[..., 1], L[..., 2]) * k
        out = cv2.cvtColor(np.dstack([nL, nC * np.cos(ang), nC * np.sin(ang)]).astype(np.float32), cv2.COLOR_Lab2BGR)
        return np.clip(out * 255, 0, 255)
    return aplicar


def prob_tela(O, tela, cl):
    LO = cv2.cvtColor(O, cv2.COLOR_BGR2Lab).astype(np.int32) // 16
    def hist(sel):
        h = np.zeros((16, 16, 16), np.float32)
        q = LO[sel]
        np.add.at(h, (q[:, 0], q[:, 1], q[:, 2]), 1)
        h = cv2.GaussianBlur(h.reshape(16, -1), (0, 0), 0.8).reshape(16, 16, 16)
        return h / max(h.sum(), 1)
    piel = cv2.erode(np.isin(cl, [2, 3]).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ts = cv2.erode(tela.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    ht = hist(ts if ts.sum() > 100 else tela)
    hp = hist(piel) if piel.sum() > 100 else np.full_like(ht, 1e-4)
    pt, pp = ht[LO[..., 0], LO[..., 1], LO[..., 2]], hp[LO[..., 0], LO[..., 1], LO[..., 2]]
    return pt / (pt + 1.5 * pp + 1e-7)


def corregir(O, B, P=None, debug=False):
    P = P or {}
    H, W = O.shape[:2]
    esc = W / 1000
    if P.get('off'):
        R = retoques(O, B, P)
        return (R, None) if debug else R
    dif = np.abs(O.astype(np.int16) - B.astype(np.int16)).max(2)
    hO, sO, vO = _hsv(O)
    hB, sB, vB = _hsv(B)
    naranjaO = ((hO <= 25) | (hO >= 175)) & (sO > 45) & (vO > 35)
    tela = (dif > 30) & naranjaO
    tela = cv2.morphologyEx(tela.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    if tela.sum() < 200:
        R = retoques(O, B, P)
        return (R, None) if debug else R
    tela_seg = cv2.erode(tela.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    # el mapa se aprende sobre la tela bien teñida (B ya con el color de la marca)
    marcaB = (dif > 60) & tela_seg
    aplicar = mapa_color(O, B, marcaB if marcaB.sum() > 200 else tela)

    cl = clases(O)
    ht_g = float(np.median(hO[tela_seg if tela_seg.sum() > 100 else tela]))
    persona = np.isin(cl, [1, 2, 3, 4])
    excl = _poly(O.shape, P['excluir']) if P.get('excluir') else np.zeros((H, W), bool)

    # logos que puso la versión de la marca: B no es mezcla entre O y el color esperado
    E0 = aplicar(O); Of0 = O.astype(np.float32); Bf0 = B.astype(np.float32)
    d0 = E0 - Of0
    t0 = np.clip(((Bf0 - Of0) * d0).sum(2) / np.maximum((d0 * d0).sum(2), 1), 0, 1)
    hB0 = cv2.cvtColor(B, cv2.COLOR_BGR2HSV).astype(np.int16)
    marca_h = int(np.median(hB0[..., 0][(dif > 60) & tela_seg])) if ((dif > 60) & tela_seg).sum() > 50 else 110
    dhb = np.minimum(np.abs(hB0[..., 0] - marca_h), 180 - np.abs(hB0[..., 0] - marca_h))
    # un logo no tiene el tono de la tela de la marca (o es blanco/gris)
    logo_g = (np.linalg.norm(Bf0 - Of0 - t0[..., None] * d0, axis=2) > P.get('resid', 50)) & (dif > 40) & ((hB0[..., 1] < 90) | ((dhb > 12) & bool(P.get('logo_color'))))
    logo_g = cv2.dilate(logo_g.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0

    # 1. prendas
    w = np.zeros((H, W), np.float32)
    letras = np.zeros((H, W), bool)
    zona_prenda = np.zeros((H, W), bool)
    if not P.get('sin_prendas'):
        ht = float(np.median(hO[tela_seg if tela_seg.sum() > 100 else tela]))
        dh = np.minimum(np.abs(hO - ht), 180 - np.abs(hO - ht))  # el tono es circular
        tono = dh <= P.get('tono', 5)
        # ropa (4) y accesorios como gorras (5), con más tolerancia de tono en los accesorios
        prenda = (((cl == 4) & tono) | ((cl == 5) & (dh <= P.get('tono_acc', 8)))) & naranjaO & ~excl
        prenda = cv2.morphologyEx(prenda.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        # ropa y accesorios por separado: una paleta naranja pegada a una pechera no es pechera
        sal = np.zeros((H, W), bool)
        for clase, minc in ((4, P.get('cubre', 0.25)), (5, P.get('cubre_acc', 0.4))):
            parte = (prenda & (cl == clase)).astype(np.uint8)
            n, lab, st, _ = cv2.connectedComponentsWithStats(parte, 8)
            cubre = np.bincount(lab[tela], minlength=n) / np.maximum(st[:, 4], 1)
            ok = (cubre > minc) & (st[:, 4] > 150 * esc * esc); ok[0] = False
            sal |= ok[lab]
        prenda = sal
        if P.get('forzar'):
            prenda |= _poly(O.shape, P['forzar']) & naranjaO
        if prenda.any():
            k = max(int(21 * esc) | 1, 7)
            zona_prenda = cv2.dilate(cv2.morphologyEx(prenda.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)),
                                     np.ones((5, 5), np.uint8)) > 0
            r = max(int(3 * esc), 2)
            a = guided(O.astype(np.float32) / 255, prenda.astype(np.float32), r, 1e-3)
            a = np.clip((a - 0.2) / 0.6, 0, 1) * (cv2.dilate(prenda.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
            # respetar logos nuevos (claros en B) y textos viejos (claros en O, ya borrados en B)
            # logo nuevo: B no es una mezcla entre el original y el color esperado
            E = aplicar(O); Of = O.astype(np.float32); Bf = B.astype(np.float32)
            d = E - Of
            t = np.clip(((Bf - Of) * d).sum(2) / np.maximum((d * d).sum(2), 1), 0, 1)
            resid = np.linalg.norm(Bf - Of - t[..., None] * d, axis=2)
            logo = (resid > P.get('resid', 50)) & (dif > 40)
            # texto viejo: más claro que la tela de alrededor
            LOg = cv2.cvtColor(O, cv2.COLOR_BGR2Lab)[..., 0].astype(np.float32)
            loc = cv2.medianBlur(LOg.astype(np.uint8), max(int(21 * esc) | 1, 5)).astype(np.float32)
            # (la versión de la marca ya lo borró: ahí B es tela teñida y no naranja)
            naranjaB = ((hB <= 25) | (hB >= 175)) & (sB > 40)
            texto = ((LOg - loc) > 10) & (dif > 60) & (sB > 140) & ~naranjaB
            # piel que MediaPipe confundió con ropa: modelo de color tela/piel de esta foto
            pr = cv2.GaussianBlur(prob_tela(O, tela, cl).astype(np.float32), (0, 0), max(4 * esc, 2))
            tol = np.where(cl == 5, P.get('tono_acc', 8), P.get('tono', 5))
            gate = np.clip((pr - 0.35) / 0.25, 0, 1) * np.clip((tol + 3 - dh) / 3, 0, 1)
            if P.get('sin_filtro'):
                gate[_poly(O.shape, P['sin_filtro'])] = 1
            a = a * gate
            res = cv2.dilate((logo | texto | logo_g).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            # el alfa suave no debe pintar sobre cosas claras/neutras que no eran tela
            w = a * ~res * np.clip((sO.astype(np.float32) - 45) / 40, 0, 1)
            # letras viejas que la versión de la marca no tapó con un logo: se borran
            logo_d = cv2.dilate((logo | logo_g).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
            letras = (w > 0.5) & ((LOg - loc) > P.get('letras_dl', 14)) & ~logo_d & (sO < 160)
            letras = cv2.morphologyEx(letras.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            n_l, lab_l, st_l, _ = cv2.connectedComponentsWithStats(letras, 8)
            okl = (st_l[:, 4] >= 6) & (st_l[:, 4] <= 900 * esc * esc); okl[0] = False
            letras = okl[lab_l]
            if P.get('sin_letras'):
                letras[:] = False

    # 2. objetos (colchonetas, banderas, fajas): cada objeto naranja vivo fuera de las
    #    personas se mira entero. Si la versión de la marca lo tiñó casi todo, se completa;
    #    si lo tiñó solo a medias (rayado), se deja como en el original.
    e = np.zeros((H, W), np.float32)
    deshacer = np.zeros((H, W), bool)
    completar = np.zeros((H, W), bool)
    vivo = (sO > P.get('s_objetos', 165)) & naranjaO & ~persona & ~excl & ~(_poly(O.shape, P['zona_rojo']) if P.get('zona_rojo') else False) & (np.minimum(np.abs(hO - ht_g), 180 - np.abs(hO - ht_g)) <= P.get('tono_obj', 8))
    vivo = cv2.morphologyEx(vivo.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    if not P.get('sin_objetos'):
        n, lab, st, _ = cv2.connectedComponentsWithStats(vivo.astype(np.uint8), 8)
        cov = np.bincount(lab[tela], minlength=n) / np.maximum(st[:, 4], 1)
        grande_o = st[:, 4] >= P.get('area_objeto', 60) * esc * esc
        # todo objeto que la versión de la marca empezó a teñir se completa (deshacer
        # podría devolverle a Medifé una prenda o una bandera)
        comp = (cov >= P.get('cov_completar', 0.08)) & grande_o; comp[0] = False
        medio = np.zeros(n, bool)
        completar = comp[lab]
        # el objeto entero: cerrar huecos (rayas más oscuras del mismo objeto)
        k7 = max(int(11 * esc) | 1, 7)
        completar = (cv2.morphologyEx(completar.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k7, k7), np.uint8)) > 0) & naranjaO & ~persona
        deshacer = medio[lab]
        if completar.any():
            pos = (completar | (tela & ~persona)).astype(np.float32)
            a = guided(O.astype(np.float32) / 255, pos, max(int(3 * esc), 2), 1e-3)
            a = np.clip((a - 0.2) / 0.6, 0, 1) * (cv2.dilate(completar.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
            # solo lo que en la versión de la marca sigue naranja: lo ya cambiado (logos, letras) queda
            sigueB = cv2.dilate((((hB <= 25) | (hB >= 175)) & (sB > 60) & (np.minimum(np.abs(hB - hO), 180 - np.abs(hB - hO)) <= 4)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            e = a * np.clip((sO.astype(np.float32) - 90) / 30, 0, 1) * ~logo_g

    m = cv2.GaussianBlur(np.maximum(w, e), (0, 0), 0.6)
    out = aplicar(O)
    mm = m[..., None]
    R = np.clip(B * (1 - mm) + out * mm, 0, 255)
    if letras.any():
        le = cv2.dilate(letras.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2) > 0
        valid = ((w > 0.5) & ~le).astype(np.float32)
        num = cv2.GaussianBlur(R * valid[..., None], (0, 0), 5)
        den = cv2.GaussianBlur(valid, (0, 0), 5)[..., None]
        fill = num / np.maximum(den, 1e-3)
        ruido = np.random.default_rng(1).normal(0, 1.8, (H, W))[..., None]
        ml = cv2.GaussianBlur(le.astype(np.float32), (0, 0), 0.8)[..., None] * (den > 0.05)
        R = R * (1 - ml) + (fill + ruido) * ml
    malp = tela & (persona | (_poly(O.shape, P['zona_rojo']) if P.get('zona_rojo') else False)) & ((hO <= P.get('rojo_hmax', ht_g - P.get('rojo_dh', 7))) | (hO > 168)) & (sO > 80) & (m < 0.1) & bool(P.get('restaurar_rojo'))
    malp = cv2.GaussianBlur(cv2.dilate(malp.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.7)[..., None]
    R = R * (1 - malp) + O * malp
    # objetos de otro tono (fajas rojas de la red, etc.): no eran de Medifé; si la versión
    # de la marca los rayó a medias, vuelven a su color original
    if not P.get('sin_cintas'):
        rojo = naranjaO & (sO > 120) & ~persona & ((hO <= ht_g - P.get('rojo_obj_dh', 4)) | (hO >= 170))
        rojo = cv2.morphologyEx(rojo.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n_r, lab_r, st_r, _ = cv2.connectedComponentsWithStats(rojo, 8)
        cov_r = np.bincount(lab_r[(dif > 30)], minlength=n_r) / np.maximum(st_r[:, 4], 1)
        sel = (cov_r > 0.05) & (cov_r < P.get('cov_rojo', 0.95)) & (st_r[:, 4] >= 80 * esc * esc); sel[0] = False
        comp_d = cv2.dilate(completar.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
        deshacer = deshacer | (sel[lab_r] & (m < 0.1) & ~comp_d)
    if deshacer.any():
        d = cv2.dilate(deshacer.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        d &= (dif > 8) & ~persona
        d = cv2.GaussianBlur(cv2.dilate(d.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)[..., None]
        R = R * (1 - d) + O * d
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(tela.astype(np.uint8), 8)
    grande = (st_[:, 4] >= P.get('area_tela', 1500) * esc * esc); grande[0] = False
    tela_g = grande[lab_]
    if P.get('s_min_tela', 0):
        mal = tela & ~persona & ~tela_g & (sO < P.get('s_min_tela', 95)) & (m < 0.1)
        mal = cv2.GaussianBlur(cv2.dilate(mal.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.7)[..., None]
        R = R * (1 - mal) + O * mal
    R = retoques(O, R.astype(np.uint8), P)
    if debug:
        dd = (B * (1 - mm) + np.array([255, 0, 255]) * mm).astype(np.uint8)
        dd[deshacer & (dif > 8)] = (255, 255, 0)
        return R, dd
    return R
