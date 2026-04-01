# 🎵 Marble Music Generator

**Pipeline automatisé pour générer des vidéos 3D "Beat Bounce" synchronisées avec du MIDI, optimisées pour TikTok.**

Un fichier MIDI en entrée → Une vidéo 3D prête à poster en sortie.

---

## 📋 Table des matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Utilisation rapide](#utilisation-rapide)
4. [Commandes détaillées](#commandes-détaillées)
5. [Architecture](#architecture)
6. [Configuration](#configuration)
7. [Thèmes](#thèmes)
8. [Layouts](#layouts)
9. [Personnalisation avancée](#personnalisation-avancée)
10. [Batch / Export multiple](#batch)
11. [FAQ & Troubleshooting](#faq)

---

## Prérequis

| Logiciel | Version | Requis |
|----------|---------|--------|
| **Blender** | ≥ 4.0 | ✅ Obligatoire |
| **Python** | ≥ 3.10 (intégré à Blender) | ✅ Obligatoire |
| **FFmpeg** | ≥ 5.0 | ✅ Pour le merge audio |
| **mido** (Python) | ≥ 1.3 | ✅ Pour le parsing MIDI |

### Optionnel
- **FluidSynth** ou **TiMidity** : pour convertir MIDI → audio
- **GPU CUDA/OptiX/Metal** : pour le rendu accéléré Cycles

---

## Installation

```bash
# 1. Cloner ou copier le projet
git clone <repo-url> marble-music
cd marble-music

# 2. Installer les dépendances Python dans Blender
# (Remplacer par votre chemin Blender)
/path/to/blender/4.x/python/bin/python3 -m pip install mido

# 3. Vérifier FFmpeg
ffmpeg -version

# 4. Test rapide
blender --background --python main.py -- --test --preview --output /tmp/test.mp4
```

### Installation mido dans Blender (détaillée)

```bash
# macOS
/Applications/Blender.app/Contents/Resources/4.0/python/bin/python3.11 -m pip install mido

# Linux
/opt/blender/4.0/python/bin/python3.11 -m pip install mido

# Windows
"C:\Program Files\Blender Foundation\Blender 4.0\4.0\python\bin\python.exe" -m pip install mido
```

---

## Utilisation rapide

### Mode test (sans MIDI)
```bash
blender --background --python main.py -- --test --output /tmp/test.mp4
```

### Avec un fichier MIDI
```bash
blender --background --python main.py -- \
    --midi ma_musique.mid \
    --audio ma_musique.mp3 \
    --output video_finale.mp4
```

### Preview rapide (Eevee, basse résolution)
```bash
blender --background --python main.py -- \
    --midi ma_musique.mid \
    --preview \
    --output preview.mp4
```

### Sauvegarder le .blend pour édition manuelle
```bash
blender --background --python main.py -- \
    --midi ma_musique.mid \
    --no-render \
    --save-blend scene.blend
```

---

## Commandes détaillées

```
blender --background --python main.py -- [OPTIONS]

Options principales:
  --midi PATH          Fichier MIDI source
  --audio PATH         Fichier audio à synchroniser (MP3, WAV)
  --output PATH        Chemin de sortie vidéo (défaut: /tmp/marble_music.mp4)

Apparence:
  --theme THEME        Thème visuel: teal, pastel, neon, dark, warm, ocean, sunset
  --layout MODE        Mode de parcours: cascade, zigzag, spiral, horizontal, vertical
  --seed INT           Graine aléatoire pour variantes reproductibles
  --ball-type TYPE     Type de bille: metallic, glass, rainbow, solid

Rendu:
  --engine ENGINE      Moteur: CYCLES (qualité) ou BLENDER_EEVEE_NEXT (vitesse)
  --fps INT            Images par seconde (30 ou 60)
  --samples INT        Échantillons de rendu Cycles (64-512)
  --resolution WxH     Résolution (défaut: 1080x1920 pour TikTok)
  --preview            Mode aperçu rapide (Eevee 540x960)

Avancé:
  --config-json PATH   Fichier JSON de configuration personnalisée
  --save-blend PATH    Sauvegarder le fichier .blend
  --no-render          Construire la scène sans rendre
  --bounce-sfx PATH    Son d'impact à ajouter aux rebonds
  --batch PATH         Mode batch (JSON avec multiple configs)
```

---

## Architecture

```
marble-music/
├── main.py                     # Point d'entrée principal
├── config.py                   # Configuration & thèmes
├── modules/
│   ├── __init__.py
│   ├── midi_parser.py          # Parsing MIDI → NoteEvents
│   ├── level_generator.py      # Notes → Plateformes & trajectoires
│   ├── scene_builder.py        # Blender: objets, matériaux, animation
│   └── audio_sync.py           # Fusion audio/vidéo (FFmpeg)
├── examples/
│   ├── batch_config.json       # Exemple config batch
│   └── custom_config.json      # Exemple config personnalisée
└── README.md
```

### Pipeline de traitement

```
MIDI File ──→ midi_parser ──→ NoteEvents
                                   │
                                   ▼
                            level_generator ──→ Platforms + Ball Keyframes
                                   │
                                   ▼
                            scene_builder ──→ Blender Scene
                                   │
                                   ▼
                            Blender Render ──→ Video (sans audio)
                                   │
                                   ▼
                            audio_sync ──→ Video + Audio = Output Final
```

---

## Configuration

### Via JSON

Créez un fichier JSON et passez-le avec `--config-json`:

```json
{
    "physics": {
        "ball_radius": 0.2,
        "restitution": 0.8,
        "min_arc_height": 1.0
    },
    "effects": {
        "enable_particles": true,
        "particle_count": 30,
        "particle_type": "sparks",
        "glow_intensity": 8.0
    }
}
```

```bash
blender --background --python main.py -- \
    --midi song.mid \
    --config-json ma_config.json \
    --output video.mp4
```

### Paramètres clés

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `physics.ball_radius` | Taille de la bille | 0.15 |
| `physics.restitution` | Élasticité des rebonds | 0.7 |
| `physics.min_arc_height` | Hauteur min. des arcs | 0.5 |
| `physics.max_arc_height` | Hauteur max. des arcs | 3.0 |
| `platform.base_spacing` | Espacement entre plateformes | 1.5 |
| `layout.vertical_drop` | Descente par plateforme | 0.4 |
| `effects.glow_intensity` | Intensité du glow d'impact | 5.0 |
| `effects.particle_count` | Nombre de particules par impact | 20 |
| `camera.focal_length` | Longueur focale caméra | 35mm |
| `camera.dof_fstop` | Ouverture profondeur de champ | f/2.8 |

---

## Thèmes

7 thèmes prédéfinis, chacun avec sa palette de couleurs, type de bille, et ambiance:

| Thème | Ambiance | Bille | Background |
|-------|----------|-------|------------|
| `teal` | Turquoise/vert, tons sombres | Métallique noire | Dégradé teal |
| `pastel` | Doux, rose/bleu/vert | Arc-en-ciel | Gris clair |
| `neon` | Cyberpunk, couleurs vives | Verre | Noir profond |
| `dark` | Élégant, sombre | Métallique noire | Noir |
| `warm` | Coucher de soleil, or | Verre | Orange |
| `ocean` | Profondeurs marines | Métallique noire | Bleu profond |
| `sunset` | Gradient chaud | Arc-en-ciel | Rouge-violet |

---

## Layouts

| Layout | Description | Idéal pour |
|--------|-------------|------------|
| `cascade` | Cascade en zigzag descendant | La plupart des morceaux |
| `zigzag` | Zigzag prononcé | Mélodies rapides |
| `spiral` | Spirale descendante | Morceaux longs |
| `horizontal` | Progression horizontale | Morceaux courts |
| `vertical` | Chute verticale | Effets dramatiques |

---

## Personnalisation avancée

### Modifier les matériaux

Générez d'abord le .blend, puis éditez manuellement:

```bash
blender --background --python main.py -- \
    --midi song.mid \
    --no-render \
    --save-blend scene_editable.blend

# Ouvrir dans Blender GUI
blender scene_editable.blend
```

### Ajouter un thème personnalisé

Éditez `config.py` et ajoutez une entrée dans `THEME_PALETTES`:

```python
ThemePreset.CUSTOM: {
    "name": "Mon thème",
    "background_top": (0.1, 0.1, 0.3),
    "background_bottom": (0.0, 0.0, 0.1),
    "platform_colors": [
        (1.0, 0.0, 0.5),
        (0.0, 1.0, 0.5),
        # ...
    ],
    "ball_color": (0.9, 0.9, 0.9),
    "ball_type": "glass",
    # ...
}
```

---

## Batch

Pour générer plusieurs variantes d'un coup:

```bash
blender --background --python main.py -- --batch examples/batch_config.json
```

Le fichier JSON de batch contient une liste de configurations:

```json
{
    "renders": [
        {"midi": "song.mid", "theme": "teal", "seed": 1, "output": "v1.mp4"},
        {"midi": "song.mid", "theme": "neon", "seed": 2, "output": "v2.mp4"},
        {"midi": "song.mid", "theme": "warm", "seed": 3, "output": "v3.mp4"}
    ]
}
```

---

## FAQ

### Le rendu est très lent
- Passez en mode Eevee: `--engine BLENDER_EEVEE_NEXT`
- Réduisez les samples: `--samples 64`
- Utilisez le mode preview: `--preview`
- Activez le GPU dans vos préférences Blender

### Pas de son dans la vidéo
- Assurez-vous de fournir `--audio` avec un fichier MP3/WAV
- Vérifiez que FFmpeg est installé

### La bille ne tombe pas bien sur les plateformes
- Ajustez `physics.min_arc_height` et `physics.max_arc_height`
- Vérifiez que le MIDI n'a pas de notes simultanées
- Essayez `--seed` différent

### Comment créer un MIDI depuis ma musique
- **MuseScore**: Export MIDI
- **FL Studio / Ableton / Logic**: Export MIDI
- **Online**: midis.fr, freemidi.org
- **Auto-transcription**: basic-pitch (Spotify), omnizart

### Formats TikTok recommandés
- Résolution: 1080x1920 (9:16)
- FPS: 60 (ou 30)
- Durée: 15s - 60s idéal
- Codec: H.264

---

## Exemples de commandes

```bash
# Vidéo rapide de test
blender -b --python main.py -- --test --preview -o test.mp4

# Production complète TikTok
blender -b --python main.py -- \
    --midi song.mid --audio song.mp3 \
    --theme neon --layout spiral --seed 42 \
    --engine CYCLES --samples 256 --fps 60 \
    -o final_tiktok.mp4

# 5 variantes automatiques
blender -b --python main.py -- --batch batch.json

# Édition manuelle ensuite
blender -b --python main.py -- \
    --midi song.mid --theme pastel \
    --no-render --save-blend editable.blend
```

---

## Licence

Projet personnel — libre d'utilisation et modification.
