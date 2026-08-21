"""
=============================================================================
main.py — Point d'entrée du Virtual Mouse par Gestes de la Main
=============================================================================
Pipeline principal :
  Webcam → HandTracker → GestureDetector → MouseController → DisplayManager

Appuyez sur [Q] ou [Échap] pour quitter proprement.
=============================================================================
"""

import sys
import io
import cv2

# ─── Fix encodage console Windows (UTF-8 requis pour les accents) ─────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Vérification des dépendances ─────────────────────────────────────────────
def _check_dependencies():
    """Vérifie que toutes les bibliothèques requises sont installées."""
    missing = []
    required = {
        "cv2":        "opencv-python",
        "mediapipe":  "mediapipe",
        "pyautogui":  "pyautogui",
        "numpy":      "numpy",
    }
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("❌ Bibliothèques manquantes :")
        for pkg in missing:
            print(f"   pip install {pkg}")
        sys.exit(1)

_check_dependencies()

# ─── Imports internes ─────────────────────────────────────────────────────────
from camera           import Camera
from hand_tracker     import HandTracker
from gesture_detector import GestureDetector, Gesture
from mouse_controller import MouseController
from display          import DisplayManager
from feedback_loop    import ImprovementLoop
from state            import FrameContext


# =============================================================================
# Boucle principale
# =============================================================================
def run() -> None:
    """
    Lance le Virtual Mouse.
    Boucle : lecture webcam → analyse → action → affichage.
    """
    print("=" * 60)
    print("   [SOURIS] Virtual Mouse — Controle par Gestes de la Main")
    print("=" * 60)
    print("  Appuyez sur [Q] ou [Echap] pour quitter")
    print("  Geste pouce+annulaire -> activer/desactiver le controle\n")

    # ── Initialisation des composants ─────────────────────────────────────────
    camera    = None
    tracker   = None
    display   = None

    try:
        camera          = Camera()          # Webcam
        tracker         = HandTracker()     # Détection MediaPipe
        detector        = GestureDetector() # Reconnaissance de gestes
        controller      = MouseController() # Contrôle souris
        display         = DisplayManager()  # Interface vidéo
        improvement_loop = ImprovementLoop() # Boucle d'amélioration continue
        frame_context   = FrameContext()

    except (RuntimeError, FileNotFoundError) as e:
        print(f"\n[ERREUR] Initialisation impossible : {e}")
        sys.exit(1)

    # ── Boucle de capture ─────────────────────────────────────────────────────
    consecutive_errors = 0
    MAX_ERRORS = 10   # Nombre d'erreurs consécutives avant abandon

    while True:
        # ── Lecture de la frame ───────────────────────────────────────────────
        success, frame = camera.read()

        if not success:
            consecutive_errors += 1
            print(f"[WARN] Erreur de lecture ({consecutive_errors}/{MAX_ERRORS})")
            if consecutive_errors >= MAX_ERRORS:
                print("[ERREUR] Trop d'erreurs consecutives. Arret.")
                break
            continue
        consecutive_errors = 0  # Réinitialiser le compteur sur succès

        # ── Détection de la main ──────────────────────────────────────────────
        frame_context.frame = frame
        hand_detected = tracker.process_frame(frame, frame_context.hand_state)

        # Dessiner les landmarks sur la frame
        tracker.draw_landmarks(frame)

        # ── Reconnaissance du geste ───────────────────────────────────────────
        frame_context.gesture_result = detector.detect(frame_context, tracker)

        # ── Action souris ──────────────────────────────────────────────────────
        if hand_detected:
            controller.handle(frame_context)

        # ── Amélioration continue ─────────────────────────────────────────────
        frame_context.raw_target = controller.last_raw_target if hand_detected else None
        frame_context.cursor_pos = controller.cursor_pos
        improvement_loop.observe(frame_context)
        if improvement_loop.should_adjust():
            improvement_loop.adjust(detector, controller)

        # ── Affichage ─────────────────────────────────────────────────────────
        display.render(frame_context)

        # ── Quitter sur [Q] ou [Échap] ────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):   # 27 = Échap
            print("\n[OK] Au revoir !")
            break

    # ── Nettoyage ──────────────────────────────────────────────────────────────
    if camera:
        camera.release()
    if tracker:
        tracker.release()
    if display:
        display.close()


# =============================================================================
# Point d'entrée
# =============================================================================
if __name__ == "__main__":
    run()
