"""
=============================================================================
hand_tracker.py — Détection et suivi de la main (MediaPipe Tasks API)
=============================================================================
Compatible avec MediaPipe 0.10+ qui utilise la nouvelle Tasks API.
Le modèle hand_landmarker.task doit être présent dans le même dossier.

Références :
  https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
=============================================================================
"""

import cv2
import numpy as np
import os

# ─── Nouvelle Tasks API MediaPipe 0.10+ ───────────────────────────────────────
from mediapipe.tasks                import python  as mp_python
from mediapipe.tasks.python         import vision  as mp_vision
from mediapipe                      import Image   as MpImage
from mediapipe                      import ImageFormat
from mediapipe.tasks.python.vision  import HandLandmarker, HandLandmarkerOptions, RunningMode
from mediapipe.tasks.python.vision  import drawing_utils as mp_drawing
from mediapipe.tasks.python.vision  import HandLandmarksConnections

from config import (
    MAX_HANDS, MIN_DETECTION_CONF, MIN_TRACKING_CONF,
    SHOW_LANDMARKS, LM_THUMB_TIP, LM_INDEX_TIP,
    LM_MIDDLE_TIP, LM_RING_TIP, LM_PINKY_TIP,
    FRAME_WIDTH, FRAME_HEIGHT
)
from state import HandState

# Chemin du fichier modèle (dans le même répertoire que ce fichier)
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")


class HandTracker:
    """
    Encapsule MediaPipe HandLandmarker (Tasks API) pour détecter et suivre
    une main en temps réel.

    Attributes
    ----------
    results   : HandLandmarkerResult | None — résultat de la dernière frame
    landmarks : list[dict]  — 21 points {"x", "y", "z"} normalisés [0.0, 1.0]
    """

    # Connexions standard de la main pour le dessin
    _HAND_CONNECTIONS = [
        (0,1),(1,2),(2,3),(3,4),         # Pouce
        (5,6),(6,7),(7,8),               # Index
        (9,10),(10,11),(11,12),          # Majeur
        (13,14),(14,15),(15,16),         # Annulaire
        (17,18),(18,19),(19,20),         # Auriculaire
        (0,5),(5,9),(9,13),(13,17),(0,17) # Paume
    ]

    def __init__(self):
        self.results   = None
        self.landmarks = []

        # Vérification de la présence du modèle
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"Modèle MediaPipe introuvable : {_MODEL_PATH}\n"
                "Téléchargez-le avec :\n"
                "  python -c \"import urllib.request; urllib.request.urlretrieve("
                "'https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                "hand_landmarker/float16/1/hand_landmarker.task', 'hand_landmarker.task')\""
            )

        # Options du HandLandmarker
        options = HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=RunningMode.IMAGE,          # Mode IMAGE (synchrone, frame par frame)
            num_hands=MAX_HANDS,
            min_hand_detection_confidence=MIN_DETECTION_CONF,
            min_hand_presence_confidence=MIN_DETECTION_CONF,
            min_tracking_confidence=MIN_TRACKING_CONF,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

    # ──────────────────────────────────────────────────────────────────────────
    # Méthode principale : traiter une frame
    # ──────────────────────────────────────────────────────────────────────────
    def process_frame(self, frame: np.ndarray, hand_state: HandState | None = None) -> bool:
        """
        Analyse une frame BGR et met à jour self.landmarks.

        Parameters
        ----------
        frame : np.ndarray — image BGR de la webcam
        hand_state : HandState | None — état partagé à remplir

        Returns
        -------
        bool — True si au moins une main est détectée
        """
        # Conversion BGR → RGB requise par MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Encapsuler dans un objet mediapipe.Image
        mp_image = MpImage(image_format=ImageFormat.SRGB, data=rgb)

        # Inférence synchrone
        self.results = self._landmarker.detect(mp_image)

        self.landmarks = []

        detected = False
        if self.results.hand_landmarks:
            # Première main détectée (MAX_HANDS=1)
            for lm in self.results.hand_landmarks[0]:
                self.landmarks.append({"x": lm.x, "y": lm.y, "z": lm.z})
            detected = True

        if hand_state is not None:
            hand_state.visible = detected
            hand_state.landmarks = list(self.landmarks)
            hand_state.confidence = 1.0 if detected else 0.0

        return detected

    # ──────────────────────────────────────────────────────────────────────────
    # Dessin des landmarks sur la frame
    # ──────────────────────────────────────────────────────────────────────────
    def draw_landmarks(self, frame: np.ndarray) -> None:
        """
        Dessine les 21 landmarks et leurs connexions sur la frame.

        Parameters
        ----------
        frame : np.ndarray — image BGR à annoter (modifiée en place)
        """
        if not SHOW_LANDMARKS or not self.landmarks:
            return

        h, w = frame.shape[:2]

        # Dessiner les connexions (os de la main)
        for (a, b) in self._HAND_CONNECTIONS:
            if a < len(self.landmarks) and b < len(self.landmarks):
                x1 = int(self.landmarks[a]["x"] * w)
                y1 = int(self.landmarks[a]["y"] * h)
                x2 = int(self.landmarks[b]["x"] * w)
                y2 = int(self.landmarks[b]["y"] * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 140, 255), 2)

        # Dessiner les points (landmarks)
        for lm in self.landmarks:
            cx = int(lm["x"] * w)
            cy = int(lm["y"] * h)
            cv2.circle(frame, (cx, cy), 5, (0, 220, 255), -1)
            cv2.circle(frame, (cx, cy), 5, (255, 255, 255),  1)

    # ──────────────────────────────────────────────────────────────────────────
    # Coordonnées pixel d'un landmark
    # ──────────────────────────────────────────────────────────────────────────
    def get_landmark_px(self, idx: int, frame_w: int, frame_h: int) -> tuple[int, int]:
        """
        Retourne les coordonnées pixel (entier) d'un landmark.

        Parameters
        ----------
        idx     : int — index du landmark (0..20)
        frame_w : int — largeur de la frame en pixels
        frame_h : int — hauteur de la frame en pixels

        Returns
        -------
        tuple (x_px, y_px) ou (0, 0) si absent
        """
        if not self.landmarks or idx >= len(self.landmarks):
            return (0, 0)
        lm = self.landmarks[idx]
        return (int(lm["x"] * frame_w), int(lm["y"] * frame_h))

    # ──────────────────────────────────────────────────────────────────────────
    # Distance normalisée entre deux landmarks
    # ──────────────────────────────────────────────────────────────────────────
    def distance(self, idx_a: int, idx_b: int) -> float:
        """
        Calcule la distance euclidienne normalisée entre deux landmarks.

        Returns
        -------
        float — distance [0.0, ~1.0] ; 1.0 si landmarks absents
        """
        if not self.landmarks:
            return 1.0
        a = self.landmarks[idx_a]
        b = self.landmarks[idx_b]
        return float(np.hypot(a["x"] - b["x"], a["y"] - b["y"]))

    # ──────────────────────────────────────────────────────────────────────────
    # Doigts levés
    # ──────────────────────────────────────────────────────────────────────────
    def fingers_up(self) -> list[bool]:
        """
        Détermine quels doigts sont levés.

        Returns
        -------
        list[bool] de longueur 5 : [pouce, index, majeur, annulaire, auriculaire]
        """
        if len(self.landmarks) < 21:
            return [False] * 5

        tips    = [LM_THUMB_TIP, LM_INDEX_TIP, LM_MIDDLE_TIP, LM_RING_TIP, LM_PINKY_TIP]
        pip_ids = [3, 6, 10, 14, 18]

        up = []
        for i, (tip_id, pip_id) in enumerate(zip(tips, pip_ids)):
            if i == 0:
                up.append(self.landmarks[tip_id]["x"] < self.landmarks[pip_id]["x"])
            else:
                up.append(self.landmarks[tip_id]["y"] < self.landmarks[pip_id]["y"])

        return up

    # ──────────────────────────────────────────────────────────────────────────
    # Nettoyage
    # ──────────────────────────────────────────────────────────────────────────
    def release(self) -> None:
        """Libère proprement les ressources MediaPipe."""
        self._landmarker.close()
