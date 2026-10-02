"""Versión 'solo logo': la foto original, sin teñir nada; solo se borra el texto de
Medifé y se pega el logo de la marca en el mismo lugar (mismo rebrand.py, recolor apagado)."""
import sys, os, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebrand
from fotos import FOTOS
marcas = [a for a in sys.argv[1:] if a in rebrand.MARCAS] or list(rebrand.MARCAS)
filtros = [a for a in sys.argv[1:] if a not in rebrand.MARCAS]
for nombre, cfg in FOTOS.items():
    if filtros and not any(f in nombre for f in filtros): continue
    c = dict(cfg); c['recolor'] = False
    for m in marcas:
        out, _ = rebrand.procesar(nombre, c, m)
        dst = os.path.join(rebrand.AQUI, 'logo', m, nombre)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        cv2.imwrite(dst[:-4] + '.png', out)
    print('ok', nombre, flush=True)
