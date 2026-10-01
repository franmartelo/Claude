import cv2, numpy as np
def terminar(sr, base, debug=False, fuerza=0.85):
    up = cv2.resize(base, (sr.shape[1], sr.shape[0]), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    srf = sr.astype(np.float32)
    # detalle real de la foto: energía de bordes en el original (ampliado)
    g = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lap = np.abs(cv2.Laplacian(cv2.GaussianBlur(g, (0, 0), 0.7), cv2.CV_32F))
    det = cv2.GaussianBlur(lap, (0, 0), 2.0)
    det = cv2.resize(det, (sr.shape[1], sr.shape[0]), interpolation=cv2.INTER_LINEAR)
    # textura inventada: lo que la IA agregó que no está en el original
    inv = cv2.GaussianBlur(np.abs(srf - up).mean(2), (0, 0), 3.0)
    w = np.clip((det - 2.0) / 6.0, 0, 1)                      # zonas enfocadas: IA
    w *= np.clip(1.0 - (inv - 6.0 - det * 0.8) / 8.0, 0, 1)   # mucha invención sin detalle: menos IA
    w = cv2.GaussianBlur(w, (0, 0), 2.0)[..., None] * fuerza
    out = srf * w + up * (1 - w)
    gr = np.random.default_rng(7).normal(0, 1.6, sr.shape[:2]).astype(np.float32)
    gr = cv2.GaussianBlur(gr, (0, 0), 0.6)[..., None]
    L = out.mean(2, keepdims=True) / 255
    out = np.clip(out + gr * (1.2 - 0.6 * L), 0, 255).astype(np.uint8)
    return (out, (w[..., 0] * 255).astype(np.uint8)) if debug else out
