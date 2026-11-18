# Droplet OS — Aura

Le système de design de Droplet OS : bureau, fenêtres, contrôles et applications système. Il prolonge **Droplet Design**, le système de la famille Droplet : même nuit, mêmes polices (Inter et Inter Tight), même couleur produit (la goutte, #FF2D55), mêmes règles de contraste et de mouvement. Aura y ajoute ce qu'un système d'exploitation demande : une matière (Liquid Glass), des mesures de bureau au point près, et les composants d'interface.

Référence visuelle : l'écran « Bureau, itération 4 » (groupe d'assets *Ecrans-reference*), validé le 17 novembre 2026, et ses cotes.

## Principes

1. **Le contenu d'abord, le verre pour les commandes.** Le Liquid Glass est réservé à la navigation et aux contrôles (barre latérale, barres d'outils, Dock, menus, widgets). Le contenu reste sur des surfaces pleines (`fenetre`, `fenetre-contenu`).
2. **Tout est concentrique.** Un élément posé dans un autre a un rayon égal au rayon du parent moins la distance au bord : fenêtre 26 → barre latérale 18 (marge 8) ; panneau 28 → tuile 24 (marge 4) ; menu 12 → élément survolé 7.
3. **Une seule lueur par écran.** La lumière vient de l'éclipse du fond d'écran ; les reflets du verre sont toujours en haut à gauche.
4. **Le mouvement décélère.** Rien ne rebondit. Tout se coupe si l'utilisateur demande moins d'animations.

## Le ton

Le système parle simplement, en phrases courtes, du côté de la personne : « Vider la corbeille ? », « 3 applications peuvent être mises à jour. ». Les boutons sont des verbes (« Vider », « Continuer »), jamais « OK ». Pas de jargon technique à l'écran : on dit « à proximité », pas « pair mDNS ».

## Couleur

- **Accent** : `goutte` pour les pictogrammes, les contrôles actifs et le focus ; `goutte-remplie` dès qu'il y a du texte blanc dessus (4,55:1).
- **Textes** : `label` (principal), `label-2` (secondaire, ≥ 4,5:1), `label-3` (décoratif seulement : titres de section, invites), `label-inactif`.
- **Surfaces** : `fenetre`, `fenetre-contenu`, et les teintes de verre `verre-capsule`, `verre-lateral`, `verre-flottant`, `verre-menu`, `verre-dock` (leur canal alpha règle la densité du verre).
- **Liserés** : `lisere-externe` et `lisere-interne` (0,5 pt) détachent chaque fenêtre ; `separateur` pour les filets.
- **Étiquettes et états** : huit couleurs d'étiquette ; `succes`, `attention`, `erreur` portent un sens, jamais une décoration.

Deux thèmes : **Sombre** (par défaut) et **Clair**. Le fond du bureau (`bureau-nuit`) ne change pas.

## Typographie

Inter pour l'interface, Inter Tight pour les titres de marque. Les tailles suivent l'échelle des Mac : `corps` 13, `appel` 12, `sous-titre` 11, `note` 10 (minimum). L'interlettrage suit la table d'Apple, taille par taille (−0,08 à 13, −0,23 à 15, −0,43 à 17). Les chiffres qui changent (heure, progression) utilisent les chiffres à chasse fixe d'Inter (`font-variant-numeric: tabular-nums`).

## Matière : Liquid Glass

Un verre Aura combine quatre couches : le fond flouté et saturé (`verre-flou`, `verre-saturation`), une teinte (jeton `verre-*`), un liseré spéculaire plus fort en haut à gauche, et une ombre douce (`ombre-verre`). En CSS : classe `aura-verre` et ses variantes `--lateral`, `--flottant`, `--menu`, `--dock`. Le rendu de référence, avec la vraie réfraction des bords, est l'écran du bureau.

## Espaces et rayons

Grille de 4. Hauteurs : barre de menus 24, contrôles 22 / 28 / 36, capsules 36, lignes de barre latérale 28. Rayons : fenêtre 26, widget 24, Dock 22, carte et dialogue 20, barre latérale 18, menu 12, champ 9, sélection 8, gélule 999.

## Iconographie

- **Marque** : l'éclipse, un croissant de lumière (groupe d'assets *Logo*), blanche dans la barre de menus, `goutte` sur les écrans de marque.
- **Icônes d'apps** : en couches de verre, voir le composant Icone et le groupe *Icones-apps*.
- **Pictogrammes** : Phosphor (MIT), 16 pt.

## Mouvement

`duree-instant` 100 ms (appui), `duree-rapide` 200 ms (menus, survols), `duree-standard` 300 ms (panneaux, fenêtres), `duree-lent` 450 ms, `duree-scene` 700 ms (thème, démarrage). Courbes : `courbe` (par défaut), `courbe-sortie` (ce qui entre).

## Utiliser le système

Charger `tokens.css` puis `components/bundle.css`, et poser les classes `aura-*` sur des éléments HTML natifs (`button`, `input`, `nav`, `a`). Chaque composant documente ses mesures, ses jetons et ses règles. L'implémentation native (Qt 6 / QML) reprend les mêmes jetons.
