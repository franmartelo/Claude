"""Genera, para una lista de fotos y marcas, la versión 'logo' (sin teñir) con flybanners firmes."""
import sys, os, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebrand, banderas
from fotos import FOTOS
marcas = [a for a in sys.argv[1:] if a in rebrand.MARCAS] or list(rebrand.MARCAS)
filtros = [a for a in sys.argv[1:] if a not in rebrand.MARCAS]
for nombre, cfg in FOTOS.items():
    if filtros and nombre not in filtros: continue
    O = cv2.imread(os.path.join(rebrand.ORIGEN, nombre))
    for m in marcas:
        c = dict(cfg); c['recolor'] = False
        banderas.instalar(nombre, O, m)
        out, _ = rebrand.procesar(nombre, c, m)
        rebrand.pegar = rebrand._pegar_original
        dst = os.path.join(rebrand.AQUI, 'logo', m, nombre[:-4] + '.png')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        cv2.imwrite(dst, out)
    print('ok', nombre, flush=True)
