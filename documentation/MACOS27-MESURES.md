# Mesures relevées dans le kit Apple « macOS 27 » (Figma)

Source : copie communautaire du kit officiel Apple Design Resources, fichier
`k9NBdqDDyWvYcS2N4eIyPG`, lue via le connecteur Figma (lecture seule) le 18/11/2026.
Unités : points macOS (1 pt = 1 px logique). Le kit sert de **référence de mesures** ;
aucun asset Apple (icônes, SF Pro, SF Symbols) n'est copié dans Droplet.

## 1. Liquid Glass (page Materials + variables « Kit »)

| Paramètre | Regular / Small | Medium / Large | Menu | Dock | Notification | Popover |
|---|---|---|---|---|---|---|
| Frost (flou) | 6 | 16 | 25 | 16 | 25 | 26 |
| Refraction | 0.70 | 0.70 | 0.70 | 0.70 | 0.70 | 0.70 |
| Depth (épaisseur du biseau) | 30 | 30 | 40 | 30 | 30 | 40 |
| Dispersion | 0.20 | 0.20 | 0.40 | 0.20 | 0.20 | 0.20 |
| Splay | 0.20 | 0.20 | 0.20 | 0.20 | 0.20 | — |
| Light intensity (angle 0°) | 0.25 | 0.25 | 0.20 | 0.10 | 0.25 | 0.15 |

Couches sous le verre (« Fill + Shadow ») :
- **Clair** : `#FFFFFF @70 %` (Lighten) + `#BFBFBF @10 %` (Darken).
- **Sombre** : `#1A1A1A @70 %` (Luminosity) + `#1A1A1A @90 %` (Luminosity) + `#1A1A1A` (Lighten).
- **Ombre portée** : 0, +18, flou 48, noir 25 % (clair) / 45 % (sombre). Menus et notifications : +8 au lieu de +18.
- **Liseré** : contour 0,5 pt `#DBDBDB` (clair) / `#A6A6A6` (sombre) en Linear Burn, plus deux reflets latéraux ±1,25 pt (spread −0,75).
- **Reflets internes** : ombres internes haut/bas à ±40 pt (spread −40, flou 10) en Linear Dodge, `#282828` (clair) / `#1A1A1A` (sombre). Elles donnent l'éclat sur les bords haut et bas.

Matériaux classiques (flou d'arrière-plan 60) :

| Type | Clair | Sombre |
|---|---|---|
| Ultra Thick | `#ECECEC @88 %` + `#333` Linear Dodge | noir 50 % |
| Thick | `#F6F6F6 @72 %` | noir 40 % |
| Medium | `#F6F6F6 @60 %` | noir 29 % |
| Thin | `#F6F6F6 @48 %` | noir 20 % |
| Ultra Thin | `#F6F6F6 @36 %` | noir 10 % |

## 2. Barre de menus

- Éléments hauts de **24**, rayon 4 ; padding 4 / 9 (nom d'app : 4 / 11 à gauche) ; pas d'espacement entre éléments.
- Le cadre du composant mesure 45 de haut (padding 10 en haut, 11 en bas autour des éléments de 24) ; pas de fond.
- Sélection : capsule (rayon 100) qui déborde de 4 pt à gauche et à droite et de 1 pt en haut, `noir 8 %` en Linear Burn.
- Typo : libellés en SF Pro Semibold 13 ; nom de l'app en SF Pro **Heavy** 13 ; logo en 16,3.
- Côté droit : icônes de 34 de large ; date et heure séparées de 8.

## 3. Dock (taille de référence : icônes de 36)

- Hauteur 55, **rayon 15**, padding 8 en haut, à gauche et à droite et 0 en bas ; espacement 9.
- Une case d'icône mesure 36 × 47 : icône 36, écart 3, puis point d'activité 4 × 4 `#707070`, et 4 en bas.
- Mise à l'échelle pour les icônes de 52 de Droplet (×1,44) : rayon ≈ 22, espacement ≈ 13, padding ≈ 11,5.
- Verre : frost 16, light 0.10 ; reflet interne 1,5 pt `#808080` à ±2,5.

## 4. Menus

- **Rayon 12**, padding 5 en haut et en bas, 12 sur les côtés.
- Éléments hauts de 24, espacement 8 entre symbole (12 de large) et libellé ; raccourcis séparés par 1.
- Survol : rectangle de **rayon 8** qui déborde de 7 pt de chaque côté de l'élément, `#E6E6E6` en Linear Burn (clair).
- Séparateur : bloc de 11 de haut, trait de 1 pt `#E6E6E6`.
- En-tête : SF Pro Bold 13 `#727272`, padding 5 en haut et 4 en bas.
- Texte : 13 pt, `#1A1A1A` ; désactivé `#BFBFBF`.

## 5. Notifications

- **344 × 77**, rayon 20 ; padding 12 / 14 / 12 / 10 ; espacement 8.
- Icône d'app 32 (dans une colonne de 40) ; vignette à droite 32, rayon 6.
- Titre SF Pro Bold 13, message Regular 13, horodatage Regular 11.
- Pile : seconde carte de 312 × 68 décalée de 16 pt de chaque côté et dépassant de 8 pt.

## 6. Fenêtres

- **Rayon 16**. Fond `#FFFFFF` (clair) / `#1E1E1E` (sombre) ; en sombre, contour intérieur blanc 20 %.
- **Ombre de la fenêtre active** : 0, +18, flou 54, noir 30 % (clair) / 57 % (sombre), plus un contour de 1 pt noir 80 %.
- **Ombre de la fenêtre inactive** : 0, +7, flou 21, noir 20 % / 35 %.
- Feux : diamètre 14, espacement 9. Couleurs : `#F06E6A`, `#FFCD30`, `#58C73B` ; inactifs `#3A3A3A` (sombre).
- Barre de titre 31 (padding 8) ; barre d'outils « Expanded » 44 (padding 8, espacement 8).
- Barre latérale :
  - largeur 240 ; zone des feux de 52 de haut, padding gauche 19 ;
  - éléments de 36, rayon 8, marges latérales 14 ;
  - en-tête de section SF Pro Bold 13 `#727272`.
- Titre : SF Pro Bold 13, symbole Semibold 15.
- Utility panel : rayon 15, ombre 0, +5, flou 20, noir 30 %.

## 7. Popovers et contrôles

- Popover : rayon 20, padding de contenu 20, espacement 8.
- Contrôles (taille Medium) : hauteur 24, rayon 6, padding de bouton 16, police 13. Small : 20 / 5. Large : 28, en capsule.
- Interrupteur : piste 54 × 24, bouton 32 × 20 (40 × 31 pendant l'appui, soit 50 × 31 pour le knob « clicked »).
- Curseur : bouton 20 × 16 (25 × 20 pendant l'appui).
- Barre d'outils : groupe de boutons en capsule de 24 de haut (padding 2) ; boutons de 20 à 24.

## 8. Couleurs (clair | sombre)

- Rose (Pink) `#FF2D55` | `#FF375F` : identique à la goutte Droplet ✔
- Bleu `#0088FF` | `#0091FF`, Rouge `#FF383C` | `#FF4245`, Vert `#34C759` | `#30D158`, Orange `#FF8D28` | `#FF9230`
- Libellés :
  - Primaire noir 85 % | blanc 85 % ;
  - Secondaire 50 % | 55 % ;
  - Tertiaire 25 % ;
  - Quaternaire 10 %.
- Fills :
  - Primaire noir 10 % | blanc 10 % ;
  - Secondaire 8 % ;
  - Tertiaire 5 %.
- Fond de fenêtre `#FFFFFF` | `#1E1E1E`.
- Sélection de tableau active `#0165E2` | `#0158D2`.

## 9. Typographie (SF Pro → Inter chez Droplet, SF Pro n'étant pas redistribuable)

| Style | Taille / interligne | Graisse (Regular / Emphasized) |
|---|---|---|
| Large Title | 26 / 32 | Regular / Bold |
| Title 1 | 22 / 26 | Regular / Bold |
| Title 2 | 17 / 22 | Regular / Bold |
| Title 3 | 15 / 20 | Regular / Semibold |
| Headline | 13 / 16 | Bold / Heavy |
| Body | 13 / 16 | Regular / Semibold |
| Callout | 12 / 15 | Regular / Semibold |
| Subheadline | 11 / 14 | Regular / Semibold |
| Footnote / Caption | 10 / 13 | Regular / Semibold |

L'interlettrage vaut 0 dans le kit, car SF Pro gère le tracking optiquement. Avec Inter, Droplet garde sa table de tracking HIG.

## 10. Écarts avec Droplet 0.2 (à corriger)

| Élément | Droplet actuel | macOS 27 | Action |
|---|---|---|---|
| Rayon des fenêtres | 26 | **16** | réduire |
| Ombre des fenêtres | uniforme | active 18/54, inactive 7/21 | deux niveaux |
| Libellé primaire | `#1D1D1F` opaque | noir 85 % | passer en alpha |
| Rayon du Dock (icônes de 52) | 22 | ≈ 22 | OK |
| Rayon des menus | 12 | 12 | OK ; survol en rayon 8 avec débord de 7 |
| Notifications | à vérifier | 344 × 77, r 20 | aligner |
| Verre : flou | une seule valeur | 6 / 16 / 25 selon la taille | trois niveaux |
| Verre : dispersion | rim seulement | 0.2 (0.4 pour les menus) | aligner |
| Nom de l'app (barre de menus) | Semibold | Heavy | Inter Black/ExtraBold |
| Sélection dans la barre de menus | rectangle | capsule qui déborde de 4 | capsule |
