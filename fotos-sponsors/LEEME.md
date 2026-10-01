# Fotos mejoradas — sitio de sponsors (YPF, Brahma, Pepsi)

Reemplazo directo de las fotos de `ypf/`, `brahma/` y `pepsi/` en
`D:\prueba\guillermo-sponsors-marcas`. Misma estructura de carpetas y mismos
nombres de archivo, así que alcanza con copiar y pisar.

## Cómo instalarlas

1. Bajá este repo como ZIP (botón verde **Code → Download ZIP**) y descomprimilo.
2. Copiá `fotos-sponsors/ypf/assets/img/` encima de
   `D:\prueba\guillermo-sponsors-marcas\ypf\assets\img\` (aceptá reemplazar).
   Lo mismo con `brahma/` y `pepsi/`.
3. Copiá también `fotos-sponsors/<marca>/wrangler.jsonc` encima del de cada carpeta
   (el Worker ahora se llama como la marca: `ypf`, `brahma`, `pepsi`).
4. En dash.cloudflare.com → **Workers & Pages** → *Subdomain* → **Change** → `balnearioguillermo`.
5. Publicá cada sitio desde su carpeta, en PowerShell:

       cd D:\prueba\guillermo-sponsors-marcas\ypf
       npx.cmd wrangler deploy

   Queda en `https://ypf.balnearioguillermo.workers.dev` (lo mismo con `brahma` y `pepsi`).
6. Probá las tres direcciones nuevas y después borrá los Workers viejos
   (`balnearioguillermo-ypf`, `-brahma`, `-pepsi`) desde Workers & Pages → Settings → Delete.

### Sitio de Medifé

`medife/wrangler.jsonc` va en `D:\prueba\guillermo-sponsors\` (la carpeta original).
Se publica igual (`npx.cmd wrangler deploy` desde esa carpeta) y queda en
`https://medife.balnearioguillermo.workers.dev`. Después se borra el Worker viejo
`balnearioguillermo`.

**Ojo:** el subdominio es de toda la cuenta. Al cambiarlo, también cambia la dirección
de la web pública del balneario (Worker `lively-cell-1130`): pasa a
`https://lively-cell-1130.balnearioguillermo.workers.dev`. Todos los links con
`martelo-francisco8` (Instagram, QR, mensajes ya mandados) dejan de andar.

No hay que tocar el HTML: las fotos nuevas tienen el doble de resolución pero la
misma proporción, y la página las sigue mostrando del mismo tamaño (se ven más
nítidas en celulares y pantallas retina).

## Qué se hizo

**1. Se terminó el cambio de marca** (en las ~50 fotos que tenían branding de Medifé):
- Las prendas (pecheras, musculosas, camperas, gorras) quedaron teñidas a medias
  en la versión anterior: costados naranjas, rayas, parches. Ahora cada prenda se
  re-tiñe entera desde la foto original, con un color parejo que respeta sombras,
  pliegues y brillos.
- Se borraron los restos de "Medifé" que quedaban pegados al logo nuevo
  (por ejemplo la "é" de "YPFé") y las letras viejas sueltas sobre la tela.
- Bordes y halos naranjas alrededor de colchonetas, banderas y bolsas: completados.
- Se deshicieron errores de la versión anterior: piel teñida de azul, shorts rojos
  rayados de azul, vetas azules en el deck de madera, halos azules en la arena.
- Nunca se toca piel ni pelo (segmentación con MediaPipe) y se respetan los logos
  nuevos de cada marca.

**2. Calidad** (todas las fotos):
- Ampliación x2 con IA (Real-ESRGAN): saca los cuadraditos de compresión JPEG y
  recupera nitidez en caras, texto y texturas.
- Para que no se note la edición, se mezcla con un 20 % de la textura original y se
  agrega un grano fino de foto (evita el look "plástico" típico de la IA).

Se revisaron una por una, a tamaño real, antes de subirlas.

## Lo que no cambió

- Logos chicos (`logo-*.png`, `guillermo-*.png`) y videos: iguales.
- Los textos de las páginas.

## Herramientas

`herramientas/` tiene los scripts usados, por si hay que rehacer alguna foto:
`restos.py` / `restos2.py` (corrección del branding), `ajustes.py` (arreglos a mano
por foto), `sr.py` + `final.py` (ampliación y terminación).
