"""
=============================================================================
mouse_controller.py — Contrôle de la souris système (PyAutoGUI)
=============================================================================
Ce module traduit les gestes reconnus en actions souris réelles :
  • Déplacement avec lissage exponentiel
  • Clics gauche / droit / double-clic
  • Défilement vertical
  • Mappage de la zone active vers l'écran complet
=============================================================================
"""

import pyautogui
import numpy as np
from collections import deque
from config import (
    SMOOTHING_FACTOR, SMOOTHING_WINDOW, MIN_MOVE_PIXELS,
    SCROLL_SPEED, SCROLL_SENSITIVITY,
    ACTIVE_ZONE_LEFT, ACTIVE_ZONE_RIGHT,
    ACTIVE_ZONE_TOP, ACTIVE_ZONE_BOTTOM,
    FRAME_WIDTH, FRAME_HEIGHT, FLIP_FRAME
)
from gesture_detector import Gesture, GestureResult
from state import FrameContext

# Désactiver le failsafe PyAutoGUI (coin de l'écran)
# ATTENTION : remettre à True en production si vous souhaitez la sécurité native
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0          # Désactiver la pause automatique entre actions


class MouseController:
    """
    Traduit les GestureResult en commandes souris réelles.

    Attributes
    ----------
    screen_w, screen_h : int   — résolution de l'écran en pixels
    _cursor_x, _cursor_y : float — position lissée courante du curseur
    _scroll_accumulator  : float — accumulateur pour le défilement
    """

    def __init__(self):
        # Récupérer la résolution réelle de l'écran
        self.screen_w, self.screen_h = pyautogui.size()

        # Position initiale du curseur (centre de l'écran)
        self._cursor_x = float(self.screen_w  / 2)
        self._cursor_y = float(self.screen_h / 2)

        # Accumulateur de défilement (évite les scrolls saccadés)
        self._scroll_accumulator = 0.0
        self._position_history = deque(maxlen=SMOOTHING_WINDOW)
        self._smoothing_factor = SMOOTHING_FACTOR
        self._min_move_pixels = MIN_MOVE_PIXELS
        self._scroll_sensitivity = SCROLL_SENSITIVITY
        self.last_raw_target = None

        print(f"[MouseController] Écran détecté : {self.screen_w}×{self.screen_h} px")

    # ──────────────────────────────────────────────────────────────────────────
    # Méthode principale : traiter un GestureResult
    # ──────────────────────────────────────────────────────────────────────────
    def handle(self, frame_context: FrameContext) -> None:
        """
        Exécute l'action souris correspondant au geste détecté.

        Parameters
        ----------
        frame_context : FrameContext — état partagé de la frame
        """
        result = frame_context.gesture_result
        if result.gesture == Gesture.NONE or result.is_paused:
            return

        if result.gesture == Gesture.MOVE:
            self._move(frame_context.hand_state.landmarks)

        elif result.gesture == Gesture.LEFT_CLICK:
            self._move(frame_context.hand_state.landmarks)
            pyautogui.click()

        elif result.gesture == Gesture.DOUBLE_CLICK:
            self._move(frame_context.hand_state.landmarks)
            pyautogui.doubleClick()

        elif result.gesture == Gesture.RIGHT_CLICK:
            self._move(frame_context.hand_state.landmarks)
            pyautogui.rightClick()

        elif result.gesture == Gesture.SCROLL:
            self._scroll(result.meta.get("scroll_dy", 0))

    # ──────────────────────────────────────────────────────────────────────────
    # Déplacement avec lissage
    # ──────────────────────────────────────────────────────────────────────────
    def _move(self, landmarks: list[dict]) -> None:
        """
        Déplace le curseur vers la position de l'index (landmark 8)
        avec un filtre de lissage exponentiel pour éviter les tremblements.

        Le mappage : zone_active → résolution écran
        """
        from config import LM_INDEX_TIP
        if not landmarks:
            return

        # Coordonnées normalisées de la pointe de l'index
        raw_x = landmarks[LM_INDEX_TIP]["x"]
        raw_y = landmarks[LM_INDEX_TIP]["y"]

        # ── Mappage de la zone active vers [0, 1] ────────────────────────────
        zone_w = ACTIVE_ZONE_RIGHT  - ACTIVE_ZONE_LEFT
        zone_h = ACTIVE_ZONE_BOTTOM - ACTIVE_ZONE_TOP

        # Clamp dans la zone active
        clipped_x = max(ACTIVE_ZONE_LEFT, min(ACTIVE_ZONE_RIGHT,  raw_x))
        clipped_y = max(ACTIVE_ZONE_TOP,  min(ACTIVE_ZONE_BOTTOM, raw_y))

        # Normalisation dans [0, 1]
        norm_x = (clipped_x - ACTIVE_ZONE_LEFT) / zone_w
        norm_y = (clipped_y - ACTIVE_ZONE_TOP)  / zone_h

        # ── Inversion X si l’affichage est en miroir pour garder la
        # correspondance entre la main vue par l'utilisateur et le curseur.
        if FLIP_FRAME:
            norm_x = 1.0 - norm_x

        # ── Conversion en pixels écran ────────────────────────────────────────
        target_x = norm_x * self.screen_w
        target_y = norm_y * self.screen_h

        self._position_history.append((target_x, target_y))
        avg_x = sum(x for x, _ in self._position_history) / len(self._position_history)
        avg_y = sum(y for _, y in self._position_history) / len(self._position_history)

        self.last_raw_target = (target_x, target_y)

        if (abs(avg_x - self._cursor_x) < self._min_move_pixels
                and abs(avg_y - self._cursor_y) < self._min_move_pixels):
            return

        # ── Filtre de lissage exponentiel ─────────────────────────────────────
        # new_pos = α × cible + (1-α) × ancienne_pos
        alpha = self._smoothing_factor
        self._cursor_x = alpha * avg_x + (1 - alpha) * self._cursor_x
        self._cursor_y = alpha * avg_y + (1 - alpha) * self._cursor_y

        # ── Déplacement absolu (plus fluide que moveTo) ───────────────────────
        pyautogui.moveTo(int(self._cursor_x), int(self._cursor_y))

    # ──────────────────────────────────────────────────────────────────────────
    # Défilement
    # ──────────────────────────────────────────────────────────────────────────
    def _scroll(self, delta_y: float) -> None:
        """
        Fait défiler la page en fonction du mouvement vertical de la main.

        Parameters
        ----------
        delta_y : float — delta normalisé (positif = vers le bas)
        """
        # Conversion en pixels virtuels
        self._scroll_accumulator += delta_y * self._scroll_sensitivity

        # Ne scroller que quand l'accumulateur dépasse un seuil
        if abs(self._scroll_accumulator) >= 1.0:
            clicks = -int(self._scroll_accumulator * SCROLL_SPEED)
            pyautogui.scroll(clicks)
            self._scroll_accumulator = 0.0

    def set_smoothing_factor(self, value: float) -> None:
        """Met à jour le facteur de lissage du curseur."""
        self._smoothing_factor = max(0.0, min(1.0, value))

    def set_min_move_pixels(self, value: int) -> None:
        """Met à jour le seuil minimal de mouvement pour ignorer le jitter."""
        self._min_move_pixels = max(0, value)

    def set_scroll_sensitivity(self, value: int) -> None:
        """Met à jour la sensibilité du défilement."""
        self._scroll_sensitivity = max(10, min(300, value))

    # ──────────────────────────────────────────────────────────────────────────
    # Accesseurs
    # ──────────────────────────────────────────────────────────────────────────
    @property
    def cursor_pos(self) -> tuple[int, int]:
        """Retourne la position lissée courante du curseur."""
        return (int(self._cursor_x), int(self._cursor_y))
