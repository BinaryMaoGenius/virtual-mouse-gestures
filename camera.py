"""
=============================================================================
camera.py — Gestion de la capture vidéo (OpenCV VideoCapture)
=============================================================================
Encapsule l'accès à la webcam avec gestion d'erreurs robuste,
vérification de disponibilité et configuration des paramètres.
=============================================================================
"""

import cv2
import numpy as np
from config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, FLIP_FRAME


class Camera:
    """
    Gère la capture vidéo depuis une webcam.

    Attributes
    ----------
    cap     : cv2.VideoCapture — objet de capture OpenCV
    is_open : bool             — True si la caméra est disponible et ouverte
    """

    def __init__(self):
        self.cap     = None
        self.is_open = False
        self._init_camera()

    # ──────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ──────────────────────────────────────────────────────────────────────────
    def _init_camera(self) -> None:
        """
        Ouvre et configure la webcam. Lève une RuntimeError si indisponible.
        """
        print(f"[Camera] Ouverture de la caméra (index={CAMERA_INDEX})...")
        self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)  # DSHOW = moins de latence sur Windows

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Impossible d'ouvrir la caméra (index {CAMERA_INDEX}).\n"
                "Vérifiez que la webcam est connectée et non utilisée par une autre application."
            )

        # Configurer la résolution souhaitée
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, 30)             # Cibler 30 FPS
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # Buffer minimal → moins de latence

        # Vérifier la résolution réellement appliquée
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Camera] Résolution : {actual_w}×{actual_h} px")

        self.is_open = True

    # ──────────────────────────────────────────────────────────────────────────
    # Lecture d'une frame
    # ──────────────────────────────────────────────────────────────────────────
    def read(self) -> tuple[bool, np.ndarray | None]:
        """
        Lit la prochaine frame de la webcam.

        Returns
        -------
        tuple (success: bool, frame: np.ndarray | None)
            • success = False si la lecture a échoué
            • frame   = image BGR ou None
        """
        if not self.is_open or self.cap is None:
            return False, None

        success, frame = self.cap.read()

        if not success or frame is None:
            return False, None

        # Retourner la frame pour l'affichage si nécessaire.
        # La détection reste basée sur les coordonnées brutes pour un mapping
        # écran plus stable et une meilleure précision des mouvements.
        return True, frame

    # ──────────────────────────────────────────────────────────────────────────
    # Libération des ressources
    # ──────────────────────────────────────────────────────────────────────────
    def release(self) -> None:
        """Libère proprement la capture vidéo."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.is_open = False
            print("[Camera] Caméra libérée.")
