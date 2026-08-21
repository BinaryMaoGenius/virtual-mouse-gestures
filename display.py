"""
=============================================================================
display.py — Interface vidéo et affichage de l'état du système
=============================================================================
Toutes les fonctions d'affichage OpenCV sont centralisées ici :
  • Bandeau d'état (geste, pause, FPS)
  • Zone active
  • Indicateurs de geste
  • Tutoriel des gestes
=============================================================================
"""

import cv2
import time
import numpy as np
from config import (
    WINDOW_NAME, SHOW_FPS, SHOW_ACTIVE_ZONE, SHOW_GESTURE_INFO,
    ACTIVE_ZONE_LEFT, ACTIVE_ZONE_RIGHT, ACTIVE_ZONE_TOP, ACTIVE_ZONE_BOTTOM,
    FRAME_WIDTH, FRAME_HEIGHT, FLIP_FRAME,
    COLOR_ACTIVE, COLOR_PAUSE, COLOR_CLICK, COLOR_RCLICK,
    COLOR_SCROLL, COLOR_WARNING, COLOR_ZONE, COLOR_TEXT, COLOR_FPS
)
from gesture_detector import Gesture, GestureResult
from state import FrameContext


# ─── Couleurs des gestes (map pour lookup rapide) ─────────────────────────────
GESTURE_COLORS = {
    Gesture.NONE        : (80,  80,  80),
    Gesture.MOVE        : COLOR_ACTIVE,
    Gesture.LEFT_CLICK  : COLOR_CLICK,
    Gesture.DOUBLE_CLICK: (255, 100, 0),
    Gesture.RIGHT_CLICK : COLOR_RCLICK,
    Gesture.SCROLL      : COLOR_SCROLL,
    Gesture.PAUSE       : COLOR_PAUSE,
}

# ─── Libellés français des gestes ─────────────────────────────────────────────
GESTURE_LABELS = {
    Gesture.NONE        : "Aucune main",
    Gesture.MOVE        : "Déplacement",
    Gesture.LEFT_CLICK  : "Clic Gauche",
    Gesture.DOUBLE_CLICK: "Double-Clic",
    Gesture.RIGHT_CLICK : "Clic Droit",
    Gesture.SCROLL      : "Défilement",
    Gesture.PAUSE       : "PAUSE",
}

# ─── Émojis / symboles des gestes ────────────────────────────────────────────
GESTURE_ICONS = {
    Gesture.NONE        : " — ",
    Gesture.MOVE        : "☞",
    Gesture.LEFT_CLICK  : "●",
    Gesture.DOUBLE_CLICK: "●●",
    Gesture.RIGHT_CLICK : "○",
    Gesture.SCROLL      : "↕",
    Gesture.PAUSE       : "||",
}


class DisplayManager:
    """
    Gère tout l'affichage OpenCV du Virtual Mouse.

    Attributes
    ----------
    _fps_buffer : deque — fenêtre glissante pour le calcul du FPS moyen
    _prev_time  : float — timestamp de la frame précédente
    """

    FPS_SMOOTHING = 15   # Nombre de frames pour moyenner le FPS

    def __init__(self):
        from collections import deque
        self._fps_buffer = deque(maxlen=self.FPS_SMOOTHING)
        self._prev_time  = time.time()
        self._fps        = 0.0

        # Créer la fenêtre OpenCV
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT)

    # ──────────────────────────────────────────────────────────────────────────
    # Méthode principale : rendre une frame annotée
    # ──────────────────────────────────────────────────────────────────────────
    def render(self, frame_context: FrameContext) -> np.ndarray:
        """
        Ajoute toutes les annotations sur la frame et l'affiche.

        Parameters
        ----------
        frame_context : FrameContext — état partagé de la frame

        Returns
        -------
        np.ndarray — frame annotée
        """
        self._update_fps()

        frame = frame_context.frame
        result = frame_context.gesture_result
        cursor_pos = frame_context.cursor_pos

        if FLIP_FRAME:
            frame = cv2.flip(frame, 1)

        # ── Fond semi-transparent (bandeau supérieur) ──────────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (FRAME_WIDTH, 60), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # ── Zone active ────────────────────────────────────────────────────
        if SHOW_ACTIVE_ZONE:
            self._draw_active_zone(frame, result.is_paused)

        # ── Informations de geste ─────────────────────────────────────────
        if SHOW_GESTURE_INFO:
            self._draw_gesture_info(frame, result)

        # ── FPS ────────────────────────────────────────────────────────────
        if SHOW_FPS:
            self._draw_fps(frame)

        # ── Position du curseur ────────────────────────────────────────────
        self._draw_cursor_info(frame, cursor_pos)

        # ── Tutoriel des gestes (panneau droit) ───────────────────────────
        self._draw_gesture_guide(frame)

        # ── Bordure colorée selon l'état ──────────────────────────────────
        if not result.meta.get("hand_visible", True):
            border_color = COLOR_WARNING
        else:
            border_color = COLOR_PAUSE if result.is_paused else GESTURE_COLORS.get(result.gesture, COLOR_ACTIVE)
        cv2.rectangle(frame, (0, 0), (FRAME_WIDTH - 1, FRAME_HEIGHT - 1), border_color, 3)

        cv2.imshow(WINDOW_NAME, frame)
        return frame

    # ──────────────────────────────────────────────────────────────────────────
    # Zone active
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_active_zone(self, frame: np.ndarray, is_paused: bool) -> None:
        """Dessine le rectangle délimitant la zone de contrôle active."""
        x1 = int(ACTIVE_ZONE_LEFT   * FRAME_WIDTH)
        y1 = int(ACTIVE_ZONE_TOP    * FRAME_HEIGHT)
        x2 = int(ACTIVE_ZONE_RIGHT  * FRAME_WIDTH)
        y2 = int(ACTIVE_ZONE_BOTTOM * FRAME_HEIGHT)

        color = COLOR_PAUSE if is_paused else COLOR_ZONE
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

        # Coins accentués
        corner_len = 18
        thickness  = 2
        corner_c   = COLOR_PAUSE if is_paused else COLOR_ACTIVE
        for cx, cy, sx, sy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
            cv2.line(frame, (cx, cy), (cx + sx*corner_len, cy), corner_c, thickness)
            cv2.line(frame, (cx, cy), (cx, cy + sy*corner_len), corner_c, thickness)

    # ──────────────────────────────────────────────────────────────────────────
    # Infos du geste
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_gesture_info(self, frame: np.ndarray, result: GestureResult) -> None:
        """Affiche le geste actuel et la barre de confiance dans le bandeau."""
        label  = GESTURE_LABELS.get(result.gesture, result.gesture)
        color  = GESTURE_COLORS.get(result.gesture, COLOR_TEXT)

        # Main hors cadre : message clair
        if not result.meta.get("hand_visible", True):
            label = "⚠️ MAIN HORS CADRE"
            color = COLOR_WARNING
        elif result.is_paused and result.gesture != Gesture.PAUSE:
            label = "⏸  CONTRÔLE DÉSACTIVÉ"
            color = COLOR_PAUSE

        # Libellé du geste
        cv2.putText(frame, label, (15, 35), cv2.FONT_HERSHEY_DUPLEX,
                    0.75, color, 2, cv2.LINE_AA)

        # Barre de confiance (si un geste actif)
        if result.confidence > 0 and result.gesture not in (Gesture.NONE, Gesture.MOVE):
            bar_x = 250
            bar_y = 28
            bar_w = int(120 * result.confidence)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + 120, bar_y + 10), (40, 40, 40), -1)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 10), color, -1)
            cv2.putText(frame, f"{int(result.confidence*100)}%",
                        (bar_x + 128, bar_y + 9), cv2.FONT_HERSHEY_SIMPLEX,
                        0.42, COLOR_TEXT, 1, cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────────────────
    # FPS
    # ──────────────────────────────────────────────────────────────────────────
    def _update_fps(self) -> None:
        """Calcule le FPS moyen sur une fenêtre glissante."""
        now = time.time()
        dt  = now - self._prev_time
        self._prev_time = now
        if dt > 0:
            self._fps_buffer.append(1.0 / dt)
        self._fps = float(np.mean(self._fps_buffer)) if self._fps_buffer else 0.0

    def _draw_fps(self, frame: np.ndarray) -> None:
        """Affiche le FPS en haut à droite."""
        txt = f"FPS: {self._fps:.0f}"
        cv2.putText(frame, txt, (FRAME_WIDTH - 100, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_FPS, 2, cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────────────────
    # Position du curseur
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_cursor_info(self, frame: np.ndarray, cursor_pos: tuple[int, int]) -> None:
        """Affiche la position pixel du curseur en bas à gauche."""
        x, y = cursor_pos
        cv2.putText(frame, f"Curseur: ({x}, {y})",
                    (10, FRAME_HEIGHT - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1, cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────────────────
    # Guide des gestes (panneau latéral droit)
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_gesture_guide(self, frame: np.ndarray) -> None:
        """Affiche un mini-guide des gestes disponibles sur le bord droit."""
        guide = [
            ("☞ Index",       "Déplacer",     COLOR_ACTIVE),
            ("● Pouce+Index", "Clic gauche",  COLOR_CLICK),
            ("○ Pouce+Majeur","Clic droit",   COLOR_RCLICK),
            ("↕ Index+Majeur","Défilement",   COLOR_SCROLL),
            ("⏸ Pouce+Ann.", "Pause",         COLOR_PAUSE),
        ]
        # Fond semi-transparent pour le guide
        gx = FRAME_WIDTH - 200
        overlay = frame.copy()
        cv2.rectangle(overlay, (gx - 5, 65), (FRAME_WIDTH - 5, 65 + len(guide)*28 + 10),
                      (12, 12, 18), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        for i, (geste, desc, col) in enumerate(guide):
            y = 85 + i * 28
            cv2.putText(frame, geste, (gx, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, col, 1, cv2.LINE_AA)
            cv2.putText(frame, desc, (gx, y + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (170, 170, 170), 1, cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────────────────
    # Nettoyage
    # ──────────────────────────────────────────────────────────────────────────
    def close(self) -> None:
        """Ferme la fenêtre OpenCV."""
        cv2.destroyAllWindows()
