"""Ajustes a mano por foto (coordenadas en píxeles de la foto web original)."""
AJUSTES = {
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
