import cv2, os, sys, importlib
sys.path.insert(0, '.')
from restos2 import corregir
import ajustes
marcas = sys.argv[1:] or ['ypf', 'brahma', 'pepsi']
fs = open('web/diff.txt').read().split()
for m in marcas:
    for f in fs:
        if not f.endswith('.jpg'): continue
        O = cv2.imread('web/orig/' + f); B = cv2.imread(f'web/{m}/' + f)
        k = f.replace('assets/img/', '')
        P = dict(ajustes.AJUSTES.get(k, {})); P.update(ajustes.AJUSTES.get(f'{m}:{k}', {})); P.setdefault('logo_color', m == 'pepsi')
        R = corregir(O, B, P)
        o = f'corr/{m}/{f}'; os.makedirs(os.path.dirname(o), exist_ok=True)
        cv2.imwrite(o, R, [cv2.IMWRITE_PNG_COMPRESSION, 1]) if o.endswith('.png') else cv2.imwrite(o[:-4] + '.png', R)
    print(m, 'ok', flush=True)
