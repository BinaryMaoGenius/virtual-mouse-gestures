"""
feedback_loop.py — Boucle d'amélioration continue du Virtual Mouse

Ce module observe les performances en temps réel et ajuste
les paramètres de lissage et de seuils de reconnaissance.
"""

import time
from collections import deque
from config import (
    SMOOTHING_WINDOW,
    MIN_MOVE_PIXELS,
    HAND_SIZE_REFERENCE,
    HAND_SIZE_MIN,
    HAND_SIZE_MAX,
)
from gesture_detector import Gesture


class ImprovementLoop:
    """Collecte des métriques et améliore les paramètres en continu."""

    ADJUST_EVERY_FRAMES = 80
    MAX_SMOOTHING = 0.30
    MIN_SMOOTHING = 0.10
    SMOOTHING_STEP = 0.02
    MAX_THRESHOLD_MULT = 1.25
    MIN_THRESHOLD_MULT = 0.75
    MIN_OBSERVATIONS = 8

    def __init__(self):
        self._frame_counter = 0
        self._movement_history = deque(maxlen=SMOOTHING_WINDOW)
        self._click_confidences = deque(maxlen=SMOOTHING_WINDOW)
        self._scroll_confidences = deque(maxlen=SMOOTHING_WINDOW)
        self._pause_confidences = deque(maxlen=SMOOTHING_WINDOW)
        self._gesture_counts = {
            Gesture.LEFT_CLICK: 0,
            Gesture.RIGHT_CLICK: 0,
            Gesture.SCROLL: 0,
            Gesture.PAUSE: 0,
            Gesture.MOVE: 0,
        }
        self._last_adjust_time = time.time()

    def observe(self, frame_context) -> None:
        """Collecte des métriques à chaque frame pertinente."""
        self._frame_counter += 1

        if frame_context.raw_target is not None:
            dx = abs(frame_context.raw_target[0] - frame_context.cursor_pos[0])
            dy = abs(frame_context.raw_target[1] - frame_context.cursor_pos[1])
            self._movement_history.append((dx, dy))

        result = frame_context.gesture_result
        if result.gesture == Gesture.LEFT_CLICK:
            self._click_confidences.append(result.confidence)
            self._gesture_counts[Gesture.LEFT_CLICK] += 1
        elif result.gesture == Gesture.RIGHT_CLICK:
            self._gesture_counts[Gesture.RIGHT_CLICK] += 1
        elif result.gesture == Gesture.SCROLL:
            self._scroll_confidences.append(result.confidence)
            self._gesture_counts[Gesture.SCROLL] += 1
        elif result.gesture == Gesture.PAUSE:
            self._pause_confidences.append(result.confidence)
            self._gesture_counts[Gesture.PAUSE] += 1
        elif result.gesture == Gesture.MOVE:
            self._gesture_counts[Gesture.MOVE] += 1

    def should_adjust(self) -> bool:
        return self._frame_counter > 0 and self._frame_counter % self.ADJUST_EVERY_FRAMES == 0

    def adjust(self, detector, controller) -> None:
        """Ajuste les paramètres du détecteur et du contrôleur en fonction des métriques."""
        if len(self._movement_history) < self.MIN_OBSERVATIONS:
            return

        avg_dx = sum(dx for dx, _ in self._movement_history) / len(self._movement_history)
        avg_dy = sum(dy for _, dy in self._movement_history) / len(self._movement_history)
        avg_movement = (avg_dx + avg_dy) / 2.0

        if self._click_confidences:
            avg_click_confidence = sum(self._click_confidences) / len(self._click_confidences)
        else:
            avg_click_confidence = 0.0

        if self._scroll_confidences:
            avg_scroll_confidence = sum(self._scroll_confidences) / len(self._scroll_confidences)
        else:
            avg_scroll_confidence = 0.0

        self._tune_smoothing(avg_movement, controller)
        self._tune_thresholds(avg_click_confidence, detector)
        self._tune_scroll(avg_scroll_confidence, controller)

    def _tune_smoothing(self, avg_movement: float, controller) -> None:
        """Ajuste le lissage en fonction du bruit de mouvement observé."""
        if avg_movement > 45 and controller._smoothing_factor < self.MAX_SMOOTHING:
            controller.set_smoothing_factor(min(self.MAX_SMOOTHING,
                                                controller._smoothing_factor + self.SMOOTHING_STEP))
        elif avg_movement < 18 and controller._smoothing_factor > self.MIN_SMOOTHING:
            controller.set_smoothing_factor(max(self.MIN_SMOOTHING,
                                                controller._smoothing_factor - self.SMOOTHING_STEP))

        if avg_movement > 35 and controller._min_move_pixels < 16:
            controller.set_min_move_pixels(min(16, controller._min_move_pixels + 2))
        elif avg_movement < 12 and controller._min_move_pixels > 4:
            controller.set_min_move_pixels(max(4, controller._min_move_pixels - 1))

    def _tune_thresholds(self, avg_click_confidence: float, detector) -> None:
        """Ajuste les seuils de détection selon la confiance moyenne des clics."""
        if avg_click_confidence < 0.40:
            detector.adjust_threshold_multiplier(1.05)
        elif avg_click_confidence > 0.80:
            detector.adjust_threshold_multiplier(0.97)

    def _tune_scroll(self, avg_scroll_confidence: float, controller) -> None:
        """Ajuste légèrement le comportement de défilement si nécessaire."""
        if avg_scroll_confidence > 0.80:
            controller.set_scroll_sensitivity(max(40, controller._scroll_sensitivity - 5))
        elif avg_scroll_confidence < 0.35:
            controller.set_scroll_sensitivity(min(160, controller._scroll_sensitivity + 5))
