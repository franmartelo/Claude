"""Ajustes a mano por foto (coordenadas en píxeles de la foto web original)."""
AJUSTES = {
    'act/staff-1.jpg': {'excluir': [[(390, 396), (478, 390), (478, 418), (436, 428), (390, 430)]]},
    # restos rojos del "Medifé" de la pantalla LED debajo del panel
    'act/eventos-2.jpg': {'borrar_rojo': [[(118, 390), (218, 390), (218, 428), (118, 428)]]},
    # anteojos espejados: el reflejo naranja no es la gorra
    'staff2.jpg': {'excluir': [[(416, 346), (470, 338), (542, 332), (542, 372), (470, 380), (416, 382)]]},
    'staff.jpg': {'excluir': [[(612, 207), (698, 204), (698, 232), (655, 241), (612, 241)]]},
    # short coral del nene (no es de Medifé): la versión anterior lo rayó de azul
    'act/escuelita-3.jpg': {'restaurar': [[(338, 398), (522, 398), (522, 522), (338, 522)]]},
    # restos de la "é" al costado del globo de Pepsi (más chico que el wordmark)
    'pepsi:act/staff-6.jpg': {'borrar_todo': [[(511, 628), (533, 628), (533, 677), (506, 677), (506, 659), (511, 652)],
                                              [(496, 626), (516, 626), (516, 658), (496, 658)]]},
    # paleta naranja (no es de Medifé)
    'act/padel-6.jpg': {'excluir': [[(296, 613), (292, 635), (280, 655), (263, 668), (244, 673), (224, 668), (207, 655), (195, 635), (192, 613), (195, 590), (207, 570), (224, 557), (244, 553), (263, 557), (280, 570), (292, 590)]]},
    # brazo al sol del jugador del medio: MediaPipe lo toma como ropa
    'padel.jpg': {'excluir': [[(436, 278), (481, 283), (485, 330), (489, 415), (480, 440), (436, 440)], [(488, 405), (528, 405), (530, 445), (488, 445)]]},
    # shorts rojos que la versión de la marca había rayado de azul
    'act/voley-4.jpg': {'restaurar_rojo': True},
    'voley.jpg': {'restaurar_rojo': True, 'rojo_hmax': 6, 'zona_rojo': [[(296, 358), (352, 358), (352, 414), (296, 414)]]},
    'act/staff-6.jpg': {
        # costado de la musculosa al sol: el color se parece a la piel, pero es tela
        'sin_filtro': [[(495, 500), (578, 500), (582, 1080), (495, 1080)]],
        'forzar': [[(530, 640), (553, 650), (557, 800), (560, 1080), (530, 1080)]],
        'restaurar': [[(569, 800), (620, 820), (650, 880), (650, 960), (600, 960), (569, 900)]],
        'borrar_s': 165,
        'borrar_todo': [[(511, 628), (533, 628), (533, 677), (506, 677), (506, 659), (511, 652)]],
        'borrar': [
                   [(448, 550), (478, 550), (482, 610), (452, 610)],
                   [(458, 700), (492, 700), (495, 770), (462, 770)]],
    },
}
