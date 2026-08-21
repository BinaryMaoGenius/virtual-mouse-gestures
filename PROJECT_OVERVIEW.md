# Virtual Mouse Gestures — Documentation de synthèse

## 1. Présentation du projet

Virtual Mouse Gestures est un système Python de contrôle de la souris par gestes detectés depuis une webcam. Il utilise MediaPipe pour extraire les landmarks de la main, OpenCV pour l'affichage et PyAutoGUI pour piloter le curseur et les actions système.

### Objectif

Permettre de piloter un ordinateur sans souris physique, uniquement par le mouvement de la main et des gestes simples. Le projet est conçu pour être modulaire, extensible et prêt à évoluer vers une boucle d'amélioration continue.

## 2. Stack technique

- Python 3.9+
- OpenCV (`opencv-python`) : capture vidéo, affichage et annotations
- MediaPipe (`mediapipe`) : détection et tracking des landmarks de la main
- PyAutoGUI (`pyautogui`) : contrôle du curseur et actions de la souris
- Numpy (`numpy`) : calculs vectoriels et manipulation de données

## 3. Architecture du code

### Modules principaux

- `main.py`
  - Point d'entrée
  - Initialise la webcam, le trackeur, le détecteur, le contrôleur, l'affichage et la boucle d'amélioration
  - Gère la boucle vidéo principale

- `camera.py`
  - Encapsule l'accès à la webcam
  - Configure la résolution, le flip et le buffer

- `hand_tracker.py`
  - Entraîne MediaPipe HandLandmarker
  - Extrait 21 landmarks normalisés
  - Fournit des utilitaires de distance et de dessin

- `gesture_detector.py`
  - Convertit les distances entre landmarks en gestes
  - Gère les états de pause, clics, double-clic, scroll et déplacement
  - Supporte désormais une remise à zéro intelligente après perte de main

- `mouse_controller.py`
  - Traduit les gestes en actions système
  - Applique un lissage exponentiel et une moyenne glissante
  - Gère le mapping de la zone active caméra vers l'écran

- `display.py`
  - Affiche les annotations OpenCV
  - Affiche la zone active, le geste courant, le FPS et le guide utilisateur

- `feedback_loop.py`
  - Observe les métriques en temps réel
  - Ajuste automatiquement les paramètres de lissage, seuils et sensibilité

## 4. Vision de progression

### Court terme

- Rendre les gestes plus robustes en présence de conditions variables (luminosité, rotation de la main, sortie du cadre)
- Ajouter l'affichage des paramètres adaptatifs dans l'interface
- Enrichir le mécanisme de feedback loop avec des journaux de performance

### Moyen terme

- Ajouter un mode calibration interactif
- Supporter plusieurs profils de main (taille, vitesse, style de geste)
- Implémenter un mode drag-and-drop par geste prolongé
- Ajouter des gestes contextualisés pour des actions clavier ou macros

### Long terme

- Passer de règles de distance à un modèle ML supervisé pour la classification des gestes
- Support multi-main et reconnaissance de gestes complexes
- Évolution vers une interface AR/VR ou un assistant mains-libres
- Déporter le moteur dans une application plus portable (desktop app, WebAssembly, mobile)

## 5. Améliorations déjà intégrées

### Boucle d'amélioration continue

- `feedback_loop.py` observe :
  - stabilité du mouvement du curseur
  - confiance des clics
  - confiance du scroll
- Il ajuste :
  - `SMOOTHING_FACTOR`
  - `MIN_MOVE_PIXELS`
  - `scroll_sensitivity`
  - multiplicateur de seuils de détection

### Robustesse hors-cadre

- `gesture_detector.py` détecte désormais quand la main disparaît du cadre pendant plus de 1,2 secondes
- l'état temporaire est réinitialisé automatiquement :
  - geste précédent
  - delta scroll antérieur
  - cooldown de clic stale
- cela évite que le contrôle reste bloqué ou que le système perde la synchronisation quand la main revient

## 6. Prochain bug à corriger

### Problème observé

Lorsque la main sort du cadre et revient, le contrôle peut rester mal calibré ou bloqué dans un état temporaire.

### Solution mise en place

- ajout d'un reset automatique après perte de main prolongée
- meilleure dissociation entre l'affichage miroir et le mappage du curseur
- maintien du mode pause uniquement si l'utilisateur l'a activé explicitement

## 7. Recommandations d'amélioration immédiate

- ajouter un indicateur visuel "Main hors cadre" dans `display.py`
- faire remonter les valeurs adaptatives dans l'interface
- proposer un mode de recalibration manuel au retour de main
- ajouter des tests unitaires sur le détecteur de gestes et le contrôleur

---

Ce document peut servir de base pour la roadmap du projet et la communication de l'évolution. N'hésite pas à me demander une version plus courte ou une transformation en `README` directement.