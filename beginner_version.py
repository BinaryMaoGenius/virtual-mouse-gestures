"""
=============================================================================
beginner_version.py — Version simple pour débutant
=============================================================================
Une version condensée en un seul fichier, sans classes, sans modules séparés.
Idéale pour comprendre les concepts de base avant d'explorer la version avancée.

Gestes disponibles :
  • Index seul → déplacer le curseur
  • Pince pouce+index → clic gauche

Comment lire ce code :
  1. On ouvre la webcam
  2. On convertit chaque image en RGB pour MediaPipe
  3. On récupère les 21 points de la main
  4. On calcule la distance pouce-index
  5. Si la distance est petite → clic !
  6. Sinon → déplacer le curseur
=============================================================================
"""

# ─── Importation des bibliothèques ────────────────────────────────────────────
import cv2          # Webcam et affichage
import mediapipe as mp  # Détection de la main
import pyautogui    # Contrôle de la souris
import numpy as np  # Calculs mathématiques
import time         # Gestion du temps (cooldown des clics)

# ─── Configuration de base ────────────────────────────────────────────────────
LARGEUR_FENETRE  = 640     # Largeur de la fenêtre vidéo
HAUTEUR_FENETRE  = 480     # Hauteur de la fenêtre vidéo
SEUIL_CLIC       = 0.05    # Distance pouce-index pour déclencher un clic
LISSAGE          = 0.15    # Facteur de lissage (0=très lisse, 1=très réactif)
COOLDOWN_CLIC    = 0.40    # Temps minimum entre deux clics (secondes)

# ─── Désactiver la sécurité PyAutoGUI ────────────────────────────────────────
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

# ─── Initialisation MediaPipe ─────────────────────────────────────────────────
mp_mains   = mp.solutions.hands
mp_dessin  = mp.solutions.drawing_utils
detecteur  = mp_mains.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)

# ─── Initialisation de la webcam ──────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  LARGEUR_FENETRE)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HAUTEUR_FENETRE)

if not cap.isOpened():
    print("❌ Impossible d'ouvrir la webcam !")
    exit(1)

# ─── Résolution de l'écran ────────────────────────────────────────────────────
ECRAN_W, ECRAN_H = pyautogui.size()

# ─── Variables d'état ─────────────────────────────────────────────────────────
curseur_x, curseur_y = ECRAN_W / 2, ECRAN_H / 2   # Position lissée du curseur
dernier_clic = 0.0                                  # Timestamp du dernier clic

print("🖱️  Virtual Mouse Débutant — Appuyez sur [Q] pour quitter")
print("   ☞  Levez l'index pour déplacer le curseur")
print("   ● Pincez pouce+index pour cliquer")

# ─── Boucle principale ────────────────────────────────────────────────────────
while True:
    succes, frame = cap.read()
    if not succes:
        continue

    # Retournement horizontal (effet miroir naturel)
    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]

    # ── Conversion BGR → RGB pour MediaPipe ──────────────────────────────────
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resultats = detecteur.process(rgb)

    geste_actuel = "Aucune main"

    if resultats.multi_hand_landmarks:
        main = resultats.multi_hand_landmarks[0]

        # Dessiner les landmarks
        mp_dessin.draw_landmarks(frame, main, mp_mains.HAND_CONNECTIONS)

        # Récupérer les coordonnées normalisées (0.0 → 1.0)
        points = main.landmark

        # Landmark 8 = pointe de l'index, Landmark 4 = pointe du pouce
        index_x = points[8].x
        index_y = points[8].y
        pouce_x = points[4].x
        pouce_y = points[4].y

        # ── Calcul de la distance pouce-index ────────────────────────────────
        distance = np.hypot(index_x - pouce_x, index_y - pouce_y)

        # ── Action : Clic ou Déplacement ? ───────────────────────────────────
        maintenant = time.time()

        if distance < SEUIL_CLIC:
            # Geste de pince → CLIC
            geste_actuel = "CLIC GAUCHE"
            if maintenant - dernier_clic > COOLDOWN_CLIC:
                pyautogui.click()
                dernier_clic = maintenant
        else:
            # Déplacer le curseur avec la pointe de l'index
            geste_actuel = "Déplacement"

            # Mappage : [0,1] → résolution écran (avec inversion X pour le miroir)
            cible_x = (1.0 - index_x) * ECRAN_W
            cible_y = index_y * ECRAN_H

            # Lissage exponentiel
            curseur_x = LISSAGE * cible_x + (1 - LISSAGE) * curseur_x
            curseur_y = LISSAGE * cible_y + (1 - LISSAGE) * curseur_y

            pyautogui.moveTo(int(curseur_x), int(curseur_y))

        # Afficher la distance sur la frame
        cv2.putText(frame, f"Dist: {distance:.3f}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # ── Affichage du geste et des instructions ────────────────────────────────
    couleur = (0, 80, 255) if "CLIC" in geste_actuel else (0, 200, 80)
    cv2.putText(frame, f"Geste: {geste_actuel}", (10, 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, couleur, 2)
    cv2.putText(frame, "Q = Quitter", (w - 130, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

    cv2.imshow("Virtual Mouse — Debutant", frame)

    # Quitter avec [Q]
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ─── Nettoyage ────────────────────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()
detecteur.close()
print("👋 Au revoir !")
