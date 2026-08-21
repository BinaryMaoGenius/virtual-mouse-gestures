"""
=============================================================================
gesture_detector.py — Reconnaissance des gestes de la main
=============================================================================
Ce module analyse les distances entre landmarks pour identifier
les gestes définis et retourner une action souris correspondante.
=============================================================================
"""

import time
from collections import deque
from dataclasses import dataclass, field
from config import (
    CLICK_THRESHOLD, RIGHT_CLICK_THRESH, SCROLL_THRESHOLD,
    PAUSE_THRESHOLD, CLICK_COOLDOWN, DOUBLE_CLICK_SPEED,
    GESTURE_CONFIRM_FRAMES,
    HAND_SIZE_REFERENCE, HAND_SIZE_MIN, HAND_SIZE_MAX,
    LM_WRIST, LM_THUMB_TIP, LM_INDEX_TIP, LM_MIDDLE_TIP, LM_RING_TIP
)
from hand_tracker import HandTracker
from state import FrameContext


# ─── Structure de résultat d'un geste ────────────────────────────────────────
@dataclass
class GestureResult:
    """
    Résultat retourné après analyse d'une frame.

    Attributes
    ----------
    gesture       : str  — nom du geste détecté (ex. "MOVE", "LEFT_CLICK", ...)
    is_paused     : bool — état du mode pause
    confidence    : float — niveau de confiance (0.0 → 1.0)
    meta          : dict — données supplémentaires (ex. scroll_dy)
    """
    gesture    : str   = "NONE"
    is_paused  : bool  = False
    confidence : float = 0.0
    meta       : dict  = field(default_factory=dict)


# ─── Gestes disponibles ───────────────────────────────────────────────────────
class Gesture:
    """Constantes nommées pour tous les gestes reconnus."""
    NONE        = "NONE"
    MOVE        = "MOVE"          # Déplacer le curseur
    LEFT_CLICK  = "LEFT_CLICK"    # Clic gauche (pince pouce-index)
    RIGHT_CLICK = "RIGHT_CLICK"   # Clic droit  (pince pouce-majeur)
    SCROLL      = "SCROLL"        # Défilement  (index+majeur rapprochés)
    PAUSE       = "PAUSE"         # Basculer pause (pince pouce-annulaire)
    DOUBLE_CLICK = "DOUBLE_CLICK" # Double-clic (deux clics rapides)


# ─── Détecteur de gestes ──────────────────────────────────────────────────────
class GestureDetector:
    """
    Analyse les landmarks d'un HandTracker et identifie le geste courant.

    La priorité de détection est :
      PAUSE > LEFT_CLICK > RIGHT_CLICK > SCROLL > MOVE

    Attributes
    ----------
    _paused         : bool  — mode pause actif
    _last_click_time : float — timestamp du dernier clic gauche
    _last_gesture   : str   — geste précédent (anti-rebond)
    _pause_cooldown : float — timestamp du dernier basculement pause
    _prev_scroll_y  : float — position Y précédente pour calcul delta scroll
    """

    PAUSE_COOLDOWN = 0.60   # Délai entre deux bascules de pause (secondes)
    NO_HAND_RESET_SECONDS = 1.20   # Temps sans main pour réinitialiser l'état interne

    def __init__(self):
        self._paused             = False
        self._last_click_time    = 0.0
        self._last_gesture       = Gesture.NONE
        self._pause_cooldown     = 0.0
        self._prev_scroll_y      = None
        self._last_seen_time     = time.time()
        self._candidate_history  = deque(maxlen=GESTURE_CONFIRM_FRAMES)
        self._threshold_multiplier = 1.0

    # ──────────────────────────────────────────────────────────────────────────
    # Méthode principale
    # ──────────────────────────────────────────────────────────────────────────
    def detect(self, frame_context: FrameContext, tracker: HandTracker) -> GestureResult:
        """
        Analyse les landmarks et retourne le geste courant.

        Parameters
        ----------
        frame_context : FrameContext — état partagé de la frame
        tracker       : HandTracker   — objet contenant les landmarks de la frame

        Returns
        -------
        GestureResult — geste identifié et métadonnées
        """
        result = GestureResult(is_paused=self._paused)

        if not tracker.landmarks:
            if time.time() - self._last_seen_time > self.NO_HAND_RESET_SECONDS:
                self._reset_state_on_loss()
            self._last_seen_time = time.time()
            self._candidate_history.clear()
            result.meta["hand_visible"] = False
            return result   # Pas de main détectée

        now = time.time()
        self._last_seen_time = now
        result.meta["hand_visible"] = True

        # ── 1. Calcul des distances clés ─────────────────────────────────────
        d_thumb_index  = tracker.distance(LM_THUMB_TIP, LM_INDEX_TIP)
        d_thumb_middle = tracker.distance(LM_THUMB_TIP, LM_MIDDLE_TIP)
        d_thumb_ring   = tracker.distance(LM_THUMB_TIP, LM_RING_TIP)
        d_index_middle = tracker.distance(LM_INDEX_TIP, LM_MIDDLE_TIP)

        fingers = tracker.fingers_up()

        # Adaptation des seuils en fonction de la taille réelle de la main
        hand_size = tracker.distance(LM_WRIST, LM_MIDDLE_TIP)
        scale = max(HAND_SIZE_MIN, min(HAND_SIZE_MAX, hand_size / HAND_SIZE_REFERENCE))
        click_threshold = CLICK_THRESHOLD * scale * self._threshold_multiplier
        right_click_threshold = RIGHT_CLICK_THRESH * scale * self._threshold_multiplier
        scroll_threshold = SCROLL_THRESHOLD * scale * self._threshold_multiplier
        pause_threshold = PAUSE_THRESHOLD * scale * self._threshold_multiplier

        candidate = self._select_gesture_candidate(
            fingers,
            d_thumb_index,
            d_thumb_middle,
            d_thumb_ring,
            d_index_middle,
            click_threshold,
            right_click_threshold,
            scroll_threshold,
            pause_threshold,
        )

        confirmed_gesture = self._confirm_gesture(candidate)

        if confirmed_gesture == Gesture.PAUSE:
            if (d_thumb_ring < pause_threshold
                    and fingers[1] and fingers[2]
                    and now - self._pause_cooldown > self.PAUSE_COOLDOWN):
                self._paused          = not self._paused
                self._pause_cooldown  = now
                result.gesture        = Gesture.PAUSE
                result.is_paused      = self._paused
                result.confidence     = self._normalize(d_thumb_ring, pause_threshold)
                self._last_gesture     = Gesture.PAUSE
                return result
            result.gesture = Gesture.NONE
            return result

        if self._paused:
            result.gesture    = Gesture.NONE
            result.is_paused  = True
            return result

        if confirmed_gesture == Gesture.LEFT_CLICK:
            dt = now - self._last_click_time
            if dt < DOUBLE_CLICK_SPEED and self._last_gesture == Gesture.LEFT_CLICK:
                result.gesture    = Gesture.DOUBLE_CLICK
                result.confidence = self._normalize(d_thumb_index, click_threshold)
                self._last_click_time = 0.0
            elif dt > CLICK_COOLDOWN:
                result.gesture        = Gesture.LEFT_CLICK
                result.confidence     = self._normalize(d_thumb_index, click_threshold)
                self._last_click_time = now
            self._last_gesture = Gesture.LEFT_CLICK
            return result

        if confirmed_gesture == Gesture.RIGHT_CLICK:
            if now - self._last_click_time > CLICK_COOLDOWN:
                result.gesture        = Gesture.RIGHT_CLICK
                result.confidence     = self._normalize(d_thumb_middle, right_click_threshold)
                self._last_click_time = now
            self._last_gesture = Gesture.RIGHT_CLICK
            return result

        if confirmed_gesture == Gesture.SCROLL:
            curr_y = tracker.landmarks[LM_INDEX_TIP]["y"]
            scroll_dy = 0
            if self._prev_scroll_y is not None:
                scroll_dy = curr_y - self._prev_scroll_y
            self._prev_scroll_y = curr_y
            result.gesture    = Gesture.SCROLL
            result.confidence = self._normalize(d_index_middle, scroll_threshold)
            result.meta       = {"scroll_dy": scroll_dy}
            self._last_gesture = Gesture.SCROLL
            return result

        if confirmed_gesture == Gesture.MOVE:
            result.gesture    = Gesture.MOVE
            result.confidence = 1.0
            self._last_gesture = Gesture.MOVE
            self._prev_scroll_y = None
            return result

        result.gesture = Gesture.NONE
        return result

    def _select_gesture_candidate(
        self,
        fingers: list[bool],
        d_thumb_index: float,
        d_thumb_middle: float,
        d_thumb_ring: float,
        d_index_middle: float,
        click_threshold: float,
        right_click_threshold: float,
        scroll_threshold: float,
        pause_threshold: float,
    ) -> str:
        """Sélectionne un geste candidat sur base de distances et d'état des doigts."""
        thumb, index, middle, ring, pinky = fingers

        if (d_thumb_ring < pause_threshold
                and index and middle
                and not ring and not pinky):
            return Gesture.PAUSE

        if d_thumb_index < click_threshold and index and not middle:
            return Gesture.LEFT_CLICK

        if d_thumb_middle < right_click_threshold and middle and not index:
            return Gesture.RIGHT_CLICK

        if d_index_middle < scroll_threshold and index and middle:
            return Gesture.SCROLL

        return Gesture.MOVE

    def _confirm_gesture(self, candidate: str) -> str:
        """Confirme un geste sur plusieurs frames pour éviter le bruit."""
        self._candidate_history.append(candidate)
        if len(self._candidate_history) < self._candidate_history.maxlen:
            return Gesture.NONE
        if all(g == self._candidate_history[0] for g in self._candidate_history):
            return self._candidate_history[0]
        return Gesture.NONE

    # ──────────────────────────────────────────────────────────────────────────
    # Utilitaire : normalisation de la confiance
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _normalize(distance: float, threshold: float) -> float:
        """Transforme une distance sous le seuil en confiance [0, 1]."""
        if threshold == 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - distance / threshold))

    def adjust_threshold_multiplier(self, value: float) -> None:
        """Ajuste le multiplicateur utilisé pour les seuils de détection."""
        self._threshold_multiplier = max(0.6, min(1.4, self._threshold_multiplier * value))

    # ──────────────────────────────────────────────────────────────────────────
    # Propriétés publiques
    # ──────────────────────────────────────────────────────────────────────────
    def _reset_state_on_loss(self) -> None:
        """Réinitialise les états temporaires lorsque la main disparaît du cadre."""
        self._last_gesture = Gesture.NONE
        self._prev_scroll_y = None
        self._last_click_time = 0.0

    @property
    def is_paused(self) -> bool:
        return self._paused
