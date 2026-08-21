"""
=============================================================================
config.py — Configuration centralisée du Virtual Mouse
=============================================================================
Tous les paramètres ajustables sont ici. Modifiez ce fichier pour adapter
le comportement sans toucher au code principal.
=============================================================================
"""

# ─── Caméra ───────────────────────────────────────────────────────────────────
CAMERA_INDEX       = 0          # Index de la webcam (0 = webcam par défaut)
FRAME_WIDTH        = 640        # Largeur du flux vidéo en pixels
FRAME_HEIGHT       = 480        # Hauteur du flux vidéo en pixels
FLIP_FRAME         = True       # Miroir horizontal uniquement pour l'affichage

# ─── Détection MediaPipe ──────────────────────────────────────────────────────
MAX_HANDS          = 1          # Nombre maximum de mains détectées
MIN_DETECTION_CONF = 0.75       # Confiance minimale pour la détection initiale
MIN_TRACKING_CONF  = 0.75       # Confiance minimale pour le suivi continu

# ─── Zone active (rectangle normalisé 0.0 → 1.0) ─────────────────────────────
# Marge interne dans le cadre caméra pour éviter les bords morts
ACTIVE_ZONE_LEFT   = 0.10       # Marge gauche (10% du cadre)
ACTIVE_ZONE_RIGHT  = 0.90       # Marge droite (90% du cadre)
ACTIVE_ZONE_TOP    = 0.10       # Marge haute (10% du cadre)
ACTIVE_ZONE_BOTTOM = 0.90       # Marge basse (90% du cadre)

# ─── Lissage du curseur (filtre exponentiel) ──────────────────────────────────
# Valeur entre 0.0 (très lisse, lent) et 1.0 (réactif, tremblant)
SMOOTHING_FACTOR   = 0.18       # Facteur de lissage du mouvement curseur
SMOOTHING_WINDOW   = 4          # Taille de fenêtre pour stabiliser la trajectoire
MIN_MOVE_PIXELS    = 8          # Seuil en pixels pour ignorer les micro-mouvements
GESTURE_CONFIRM_FRAMES = 2      # Nombre de frames identiques pour valider un geste
HAND_SIZE_REFERENCE = 0.23       # Taille moyenne normalisée de la main pour adapter les seuils
HAND_SIZE_MIN      = 0.70       # Facteur minimum d'adaptation des seuils
HAND_SIZE_MAX      = 1.35       # Facteur maximum d'adaptation des seuils

# ─── Seuils de gestes (distance normalisée entre landmarks) ──────────────────
CLICK_THRESHOLD    = 0.040      # Distance pouce-index → clic gauche
RIGHT_CLICK_THRESH = 0.040      # Distance pouce-majeur → clic droit
SCROLL_THRESHOLD   = 0.060      # Distance entre index et majeur → mode défilement
PAUSE_THRESHOLD    = 0.045      # Pouce-annulaire → basculer mode pause

# ─── Comportement des clics ───────────────────────────────────────────────────
CLICK_COOLDOWN     = 0.35       # Délai minimum entre deux clics (secondes)
DOUBLE_CLICK_SPEED = 0.30       # Délai max entre deux clics → double-clic

# ─── Défilement (scroll) ──────────────────────────────────────────────────────
SCROLL_SPEED       = 10          # Nombre de "clics" de molette par action
SCROLL_SENSITIVITY = 100         # Pixels de mouvement vertical pour déclencher scroll

# ─── Affichage (interface vidéo) ──────────────────────────────────────────────
WINDOW_NAME        = "🖱️  Virtual Mouse — Contrôle par Gestes"
SHOW_FPS           = True       # Afficher le compteur FPS
SHOW_LANDMARKS     = True       # Afficher les landmarks MediaPipe
SHOW_ACTIVE_ZONE   = True       # Afficher le rectangle de la zone active
SHOW_GESTURE_INFO  = True       # Afficher le geste détecté en cours

# ─── Couleurs (format BGR pour OpenCV) ───────────────────────────────────────
COLOR_ACTIVE       = (0,   255, 120)   # Vert vif — élément actif / mode activé
COLOR_PAUSE        = (0,   165, 255)   # Orange   — mode pause
COLOR_CLICK        = (255,  50,  50)   # Rouge    — clic gauche
COLOR_RCLICK       = (255,  50, 200)   # Rose     — clic droit
COLOR_SCROLL       = (255, 200,   0)   # Jaune    — défilement
COLOR_WARNING      = (0,   180, 255)   # Bleu clair — état attention
COLOR_ZONE         = (80,  80,  80)    # Gris     — zone active
COLOR_TEXT         = (220, 220, 220)   # Blanc cassé — texte général
COLOR_FPS          = (0,   200, 255)   # Cyan     — affichage FPS

# ─── Identifiants des landmarks MediaPipe ────────────────────────────────────
# Référence : https://mediapipe.dev/solutions/hands
LM_WRIST           = 0
LM_THUMB_TIP       = 4
LM_INDEX_TIP       = 8
LM_INDEX_MCP       = 5    # Articulation de la base de l'index
LM_MIDDLE_TIP      = 12
LM_RING_TIP        = 16
LM_PINKY_TIP       = 20
