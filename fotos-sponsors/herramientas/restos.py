"""Tiñe los restos naranjas de Medifé que quedaron pegados a la tela ya re-teñida.

Para cada foto aprende, comparando original y versión de la marca, cómo es el
naranja de la tela en esa foto (y cómo es la piel), y solo toca píxeles con ese
color que estén pegados a la tela."""
import numpy as np, cv2, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
S = '/tmp/claude-0/-home-user-Claude/559bbc7f-ba77-553d-93c3-9e7cab1bef04/scratchpad/'
_seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=S + 'models/selfie.tflite'), output_category_mask=True))


def clases(img):
    r = _seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img[..., ::-1])))
    return np.squeeze(r.category_mask.numpy_view()).copy()


def lab8(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2Lab).astype(np.int32)


def hist(lab, sel, b=16):
    q = (lab[sel] // b)
    h = np.zeros((256 // b,) * 3, np.float32)
    np.add.at(h, (q[:, 0], q[:, 1], q[:, 2]), 1)
    h = cv2.GaussianBlur(h.reshape(h.shape[0], -1), (0, 0), 0.8).reshape(h.shape)  # suavizado leve
    return h / max(h.sum(), 1)


def _box(x, r):
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))


def guided(I, p, r, eps):
    """Guided filter de He et al. con guía en color."""
    mI = _box(I, r); mp_ = _box(p, r)
    cov = _box(I * p[..., None], r) - mI * mp_[..., None]
    var = np.empty(I.shape[:2] + (3, 3), np.float32)
    for i in range(3):
        for j in range(i, 3):
            v = _box(I[..., i] * I[..., j], r) - mI[..., i] * mI[..., j]
            var[..., i, j] = var[..., j, i] = v
    var += np.eye(3, dtype=np.float32) * eps
    a = np.linalg.solve(var, cov[..., None])[..., 0]
    b = mp_ - (a * mI).sum(2)
    return (_box(a, r) * I).sum(2) + _box(b, r)


def _poly(shape, polys):
    z = np.zeros(shape[:2], np.uint8)
    for p in polys:
        cv2.fillPoly(z, [np.array(p, np.int32)], 1)
    return z > 0


def retoques(O, R, P):
    """Arreglos a mano: restaurar el original (piel teñida por error) y borrar textos claros."""
    if P.get('restaurar'):
        z = cv2.GaussianBlur(_poly(R.shape, P['restaurar']).astype(np.float32), (0, 0), 1.5)[..., None]
        R = (R * (1 - z) + O * z).astype(np.uint8)
    # letras rojas sueltas (pantallas LED): solo los píxeles rojos, rellenados con lo de alrededor
    for p in P.get('borrar_rojo', []):
        z = _poly(R.shape, [p])
        hsv = cv2.cvtColor(R, cv2.COLOR_BGR2HSV)
        rojo = z & ((hsv[..., 0] <= 12) | (hsv[..., 0] >= 165)) & (hsv[..., 1] > 90)
        mask = cv2.dilate(rojo.astype(np.uint8) * 255, np.ones((3, 3), np.uint8), iterations=1)
        R = cv2.inpaint(R, mask, 3, cv2.INPAINT_TELEA)
    tareas = [(p, False) for p in P.get('borrar', [])] + [(p, True) for p in P.get('borrar_todo', [])]
    for p, todo in tareas:
        z = _poly(R.shape, [p])
        hsv = cv2.cvtColor(R, cv2.COLOR_BGR2HSV)
        claro_all = (hsv[..., 1] < P.get('borrar_s', 110)) & (hsv[..., 2] > P.get('borrar_v', 120))
        claro = z if todo else (z & claro_all)
        claro = cv2.dilate(claro.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=P.get('borrar_dilatar', 1)) > 0
        # relleno con el promedio de la tela de alrededor (sin los píxeles claros), y su grano
        # color de la tela vecina: el tono saturado dominante en un anillo alrededor
        anillo = (cv2.dilate(z.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0) & ~claro
        hh, ss = hsv[..., 0].astype(np.int16), hsv[..., 1]
        sel = anillo & (ss > 80)
        h0 = int(np.median(hh[sel])) if sel.sum() > 20 else 110
        dh = np.minimum(np.abs(hh - h0), 180 - np.abs(hh - h0))
        valid = (~claro & (dh < 12) & (ss > 60)).astype(np.float32)
        if P.get('borrar_letras_color', True) and not todo:
            # letras de otro color (blancas o naranjas) sobre la tela
            claro = z & ~((dh < 12) & (ss > 60))
            claro = cv2.dilate(claro.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=P.get('borrar_dilatar', 1)) > 0
            valid = (~claro & (dh < 12) & (ss > 60)).astype(np.float32)
        sig = P.get('borrar_sigma', 8)
        num = cv2.GaussianBlur(R.astype(np.float32) * valid[..., None], (0, 0), sig)
        den = cv2.GaussianBlur(valid, (0, 0), sig)[..., None]
        relleno = num / np.maximum(den, 1e-3)
        ruido = np.random.default_rng(0).normal(0, P.get('grano', 2.0), R.shape[:2])[..., None]
        m = cv2.GaussianBlur(claro.astype(np.float32), (0, 0), 0.7)[..., None]
        R = np.clip(R * (1 - m) + (relleno + ruido) * m, 0, 255).astype(np.uint8)
    return R


def corregir(O, B, P=None, debug=False):
    P = P or {}
    if P.get('off'):
        R = retoques(O, B, P)
        return (R, None) if debug else R
    H, W = O.shape[:2]
    esc = W / 1000
    dif = np.abs(O.astype(np.int16) - B.astype(np.int16)).max(2)
    hsvO = cv2.cvtColor(O, cv2.COLOR_BGR2HSV)
    hO, sO, vO = hsvO[..., 0], hsvO[..., 1], hsvO[..., 2]
    naranjaO = (((hO <= 24) | (hO >= 176)) & (sO > 60) & (vO > 35))
    tela = (dif > 30) & naranjaO
    tela = cv2.morphologyEx(tela.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    if tela.sum() < 200:
        R = retoques(O, B, P)
        return (R, None) if debug else R
    cl = clases(O)
    piel = np.isin(cl, [1, 2, 3])
    piel_seg = cv2.erode(piel.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    tela_seg = cv2.erode(tela.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    LO = lab8(O)
    ht = hist(LO, tela_seg if tela_seg.sum() > 100 else tela)
    neg = (piel_seg | (~cv2.dilate(tela.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool))) & ~tela
    hn = hist(LO, neg & naranjaO) if (neg & naranjaO).sum() > 100 else np.full_like(ht, 1e-4)
    q = LO // 16
    pt, pn = ht[q[..., 0], q[..., 1], q[..., 2]], hn[q[..., 0], q[..., 1], q[..., 2]]
    prob = pt / (pt + pn * P.get('peso_piel', 1.5) + 1e-6)
    r = max(int(P.get('radio', 14) * esc), 4)
    cerca = cv2.dilate(tela.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    cand = cerca & (dif <= 30) & naranjaO & (prob > P.get('umbral', 0.6))
    # nunca sobre piel o pelo (MediaPipe), con un margen chico
    cand &= ~(cv2.dilate(piel.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
    if P.get('excluir'):
        z = np.zeros((H, W), np.uint8)
        for p in P['excluir']:
            cv2.fillPoly(z, [np.array(p, np.int32)], 1)
        cand &= z == 0
    # solo las manchas que tocan la tela (crecimiento iterativo)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), 8)
    tdil = cv2.dilate(tela.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ok = np.zeros(n, bool); ok[np.unique(lab[cand & tdil])] = True; ok[0] = False
    cand = ok[lab]
    # zonas marcadas a mano: todo el naranja de adentro es tela, aunque parezca piel
    if P.get('forzar'):
        z = np.zeros((H, W), np.uint8)
        for p in P['forzar']:
            cv2.fillPoly(z, [np.array(p, np.int32)], 1)
        hO_, sO_ = hO.astype(np.int16), sO.astype(np.int16)
        cand |= (z > 0) & (dif <= 30) & (((hO_ <= 26) | (hO_ >= 174)) & (sO_ > P.get('s_forzar', 45)) & (vO > 35))
        prob = np.where(z > 0, 1.0, prob)
    # mate suave: semillas binarias refinadas con guided filter sobre el original,
    # así el borde sigue el borde real de la tela y no queda serruchado
    pos = (tela | cand).astype(np.float32)
    rg = max(int(P.get('r_guia', 4) * esc), 2)
    alfa = guided(O.astype(np.float32) / 255, pos, rg, P.get('eps', 2e-3))
    alfa = np.clip((alfa - 0.15) / 0.7, 0, 1)
    # no crecer lejos de las semillas ni meterse en la piel
    zona = cv2.dilate(pos.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    alfa *= zona
    piel_n = cv2.erode(piel.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    alfa[piel_n & ~(cand | tela)] = 0
    # lo que ya estaba teñido queda como está: solo se suma lo que falta
    viejo = np.clip(cv2.GaussianBlur(tela.astype(np.float32), (0, 0), 0.7), 0, 1)
    hB = cv2.cvtColor(B, cv2.COLOR_BGR2HSV)
    sigue_naranja = (((hB[..., 0] <= 26) | (hB[..., 0] >= 174)) & (hB[..., 1] > 40))
    sigue_naranja = cv2.dilate(sigue_naranja.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    m = np.clip(alfa - viejo, 0, 1) * sigue_naranja
    if P.get('forzar'):
        # adentro de las zonas a mano se re-tiñe todo desde el original (color parejo),
        # salvo los logos claros que ya puso la versión de la marca
        zf = _poly(O.shape, P['forzar'])
        hb = cv2.cvtColor(B, cv2.COLOR_BGR2HSV)
        naranja_b = ((hb[..., 0] <= 30) | (hb[..., 0] >= 172)) & (hb[..., 1] > 35)
        logo = (hb[..., 1] < 100) & (hb[..., 2] > 130) & ~naranja_b
        logo = cv2.dilate(logo.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        # todo lo de adentro es la prenda: el mapa de croma deja los neutros (cadenita, silbato) casi igual
        borde = cv2.GaussianBlur(zf.astype(np.float32), (0, 0), 1.2)
        borde = np.maximum(borde, alfa * cv2.dilate(zf.astype(np.uint8), np.ones((7, 7), np.uint8)))
        m = np.where(borde > 0.01, np.maximum(borde * (~logo), m * (~zf)), m)
    m = cv2.GaussianBlur(m, (0, 0), 0.6)
    if m.sum() < 5:
        R = retoques(O, B, P)
        return (R, None) if debug else R
    # mapa de color: cómo pasó el original al color de la marca en esta foto
    LB = cv2.cvtColor(B.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
    LOf = cv2.cvtColor(O.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)
    t = tela_seg if tela_seg.sum() > 100 else tela
    a, b = np.polyfit(LOf[..., 0][t], LB[..., 0][t], 1)
    cO = np.hypot(LOf[..., 1], LOf[..., 2])
    k = np.median(np.hypot(LB[..., 1][t], LB[..., 2][t]) / np.maximum(cO[t], 1))
    ang = np.arctan2(np.median(LB[..., 2][t]), np.median(LB[..., 1][t]))
    nL = np.clip(a * LOf[..., 0] + b, 1, 99)
    nC = cO * k
    out = cv2.cvtColor(np.dstack([nL, nC * np.cos(ang), nC * np.sin(ang)]).astype(np.float32), cv2.COLOR_Lab2BGR) * 255
    mm = np.clip(m, 0, 1)[..., None]
    res = retoques(O, np.clip(B * (1 - mm) + out * mm, 0, 255).astype(np.uint8), P)
    if debug:
        d = (B * (1 - mm) + np.array([255, 0, 255]) * mm).astype(np.uint8)
        return res, d
    return res
