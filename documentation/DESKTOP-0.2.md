# Droplet OS 0.2 « Aura » — le bureau

Session Wayland sur KWin 6.6, avec le shell Droplet (C++23 / QML, Qt 6.10).

## Composants

| Dossier | Rôle |
|---|---|
| `desktop/shell/` | `droplet-shell` : barre de menus, Dock, recherche, centre de contrôle, menus, notifications (serveur `org.freedesktop.Notifications`), widgets, fond d'écran vivant |
| `desktop/effects/liquidglass/` | effet KWin « Verre liquide Droplet » (`dropletglass`) : remplace le flou de KWin ; lentille, dispersion, givre, teinte adaptative, reflets, ombre (`liquidglass.frag`) |
| `desktop/session/` | `startdroplet`, `droplet-session-init`, `droplet.desktop` (session Wayland) |
| `desktop/theme/` | décorations de fenêtre Aurorae (`DropletSombre`, `DropletClair`), palettes de couleurs, `/etc/xdg/{kdeglobals,kwinrc}`, thème SDDM `droplet` |
| `desktop/packaging/build-deb.sh` | construit `droplet-desktop_0.2.0_amd64.deb` |
| `aura/render/` | rendus Python : fonds, transitions, planètes, nuages, prototypes du verre (même shader) |

## Ce qui est réel (aucun bouton fictif)

- Wi-Fi : `nmcli` ; Bluetooth : `rfkill` ; volume : `wpctl` ; luminosité : `brightnessctl` ;
  batterie : `/sys/class/power_supply` ; stockage : `QStorageInfo`.
  Si le matériel est absent, la commande est affichée « Indisponible », sans faux état.
- Apparence : palette (`plasma-apply-colorscheme`), icônes, décoration des fenêtres, verre et fond
  d'écran changent ensemble.
- Veille, redémarrage, extinction : `systemctl` (confirmation pour les deux derniers) ;
  « Fermer la session » quitte le shell, ce qui termine KWin et la session.
- Dock : lanceurs `.desktop` réellement installés + fenêtres ouvertes (modèle de tâches de Plasma).
- Menu de l'app : actions de fenêtre via KWin (réduire, agrandir, plein écran, fermer, nouvelle fenêtre).

## Fond d'écran vivant

- Jour : le jardin ; les nuages dérivent (parallaxe) et changent lentement de forme (trois états
  fondus), deux vols d'oiseaux traversent le ciel en entrant et sortant hors champ.
- Nuit : l'éclipse puis les huit planètes, **une par heure** (même règle sur l'écran de
  connexion). On passe toujours par l'éclipse : la planète redevient silhouette, change de taille,
  puis le soleil glisse et éclaire la suivante.
- Changer d'apparence joue la transition dessinée (l'éclipse s'ouvre, l'artiste trace le jardin
  et les nuages) ou son inverse.
- Les films et images sont produits par `aura/render/export_wallpapers.py OUT 1920 1200`
  (≈ 40 min sur 2 cœurs) puis empaquetés par `build-deb.sh` (`DROPLET_WALLPAPERS=OUT`).

## Construire

```bash
# dans un chroot Ubuntu 26.04 avec les dépendances de développement (voir base/hooks)
python3 aura/render/export_wallpapers.py out/wallpapers 1920 1200
./desktop/packaging/build-deb.sh out/debs
sudo ./base/build.sh                      # LAYERS=desktop par défaut
sudo python3 tests/vm/vmtest.py desktop out/droplet-os-0.2.0-vm-amd64.iso /tmp/vmt
```

## Limites connues

- Le verre liquide demande la composition OpenGL. En rendu logiciel sans OpenGL (QPainter),
  le shell dessine un verre de repli (teinte + liseré + ombre), sans lentille.
- Dans une VM sans accélération (TCG + llvmpipe), tout fonctionne mais lentement ;
  les mesures de performance ne valent que pour du vrai matériel.
- L'effet réutilise le protocole de flou de KDE : il remplace donc l'effet « Flou » de KWin
  (désactivé dans `kwinrc`).
- En VM sans KVM (émulation TCG de QEMU 8.2), llvmpipe plante sur l'AVX émulé avec `-cpu max` :
  utiliser un processeur sans AVX (`-cpu Nehalem-v2`), comme le fait `tests/vm/vmtest.py desktop`.
  Le mode jour (nuages et oiseaux animés) y est très lent ; sur du vrai matériel, ce n'est pas mesuré.
- Pas d'écran de verrouillage en 0.2 (KWin est lancé avec `--no-lockscreen`), faute d'interface de
  déverrouillage Droplet : l'écran ne se verrouille jamais tout seul.

## Performances (0.2.1)

Mesuré dans la session de test sans GPU (llvmpipe, 2 cœurs) et dans QEMU sans KVM.

| Correctif | Effet mesuré |
|---|---|
| Ciel du jour sur sa propre surface (bande du haut), cadence 12 Hz, oiseaux en images pré-rendues au lieu d'un Canvas repeint, pause la nuit / pendant les films / fenêtre maximisée / « animations instantanées » | shell en mode jour : **72 % → 14 %** d'un cœur |
| Shader du verre : flou sur chaîne de mipmaps (9 lectures au lieu de 40), dispersion seulement au bord, normale analytique, plus de lecture de fond hors du verre | **≈ 3× moins cher** par image (167 → 58 ms pour 4 surfaces en llvmpipe) |
| Effet KWin : re-lecture du fond seulement si une fenêtre *en dessous* a changé ; repeint seulement la zone modifiée quand une région change | plus de relecture à chaque image du shell |
| Horloge de la barre de menus réveillée à la minute (au lieu de chaque seconde), widgets réveillés au changement de jour | une image par minute au lieu d'une par seconde |
| Sondage réseau/son/luminosité : 30 s, 2 s seulement quand le centre de contrôle est ouvert | 15× moins de processus lancés |
| Écran de connexion : horloge à la minute, nuages à 12 Hz | — |

**Limite de mesure en VM.** Sous émulation TCG, une seule image de KWin coûte plus de 100 ms.
Qt Wayland considère alors la fenêtre comme « non exposée » (délai des rappels de trame de
100 ms, fixe), puis la ré-expose et la redessine au rappel suivant : une boucle qui occupe le
processeur en permanence, quel que soit le contenu. Elle n'existe pas quand une image coûte
moins de 100 ms (tout GPU, et llvmpipe natif à cette définition). Les chiffres de charge de la
VM ne sont donc pas représentatifs ; il faut mesurer sur la vraie machine (clé USB, ou VM avec
KVM / accélération 3D).

## Mouvement (système d'animation)

Toutes les animations du shell utilisent cinq caractères définis dans `Theme.qml` et générés par
`aura/render/motion.py`. Ce sont des ressorts à la manière d'Apple (réponse et amortissement),
simulés puis ajustés en courbes de Bézier par morceaux (erreur maximale de 0,005) :

| Caractère | Ressort | Durée | Usage |
|---|---|---|---|
| doux | 0,42 s, ζ = 1 | 514 ms | panneaux, tailles, mises en page (aucun dépassement) |
| vif | 0,28 s, ζ = 0,86 | 311 ms | pression, interrupteurs, sélection, apparition en fondu |
| rebond | 0,48 s, ζ = 0,72 | 551 ms | ouverture des popovers, Dock, notifications (dépassement de 3,8 %) |
| sortie | Bézier (0,30, 0, 0,80, 0,15) | 200 ms | fermetures : tout part plus vite que ça n'arrive |
| fondu | Bézier (0,25, 0,1, 0,25, 1) | 180 ms | couleurs, textes |

`Ressort.qml` applique un caractère à une animation ; `Pression.qml` donne le retour de pression
commun à tout ce qui se clique (enfoncement « vif », retour « rebond »). Avec « Réduire les
animations » (AnimationDurationFactor = 0), les mouvements deviennent immédiats et les fondus
sont conservés.

Les micro-interactions, élément par élément :

- **Verre** : les formes se matérialisent et se dissolvent dans le compositeur (`presence` dans
  `liquidglass.frag`), avec les mêmes durées que le contenu. Le verre suit chaque image des
  popovers pendant leur ressort.
- **Popovers** : ils s'ouvrent depuis leur point d'attache.
  - Menus : depuis le coin haut gauche, à partir de 0,97.
  - Centre de contrôle : depuis le coin haut droit, à partir de 0,93.
  - Recherche et dialogues : depuis le centre, à partir de 0,94 et 0,90.
- **Menus** : le survol suit le pointeur sans fondu. L'élément choisi clignote une fois
  (70 ms éteint, 70 ms allumé) avant la fermeture, comme sur macOS.
- **Dock** :
  - l'icône s'assombrit sous la pression ;
  - au lancement, elle rebondit en boucle (vol balistique) jusqu'à l'arrivée de la fenêtre ;
  - le point d'activité apparaît en fondu ;
  - l'étiquette monte de 4 pt en apparaissant ;
  - la géométrie de chaque icône est publiée pour la réduction en « génie ».
- **Centre de contrôle** :
  - les pictogrammes rebondissent quand leur état change ;
  - les curseurs gonflent de 2 pt quand on les tient ;
  - un clic fait glisser la valeur, un glissement la suit exactement.
- **Recherche** : les résultats arrivent en cascade (12 ms d'écart) et la sélection glisse d'une
  ligne à l'autre.
- **Notifications** :
  - à l'arrivée, elles glissent avec le ressort « rebond » ;
  - au survol, un bouton de fermeture apparaît ;
  - un balayage vers la droite les supprime (au-delà de 70 pt), sinon elles reviennent en
    ressort.
- **Écran de connexion** :
  - à l'arrivée, l'horloge, l'avatar, le champ puis les boutons apparaissent avec 60 ms d'écart ;
  - un anneau de focus s'affiche autour du champ ;
  - la flèche apparaît dès qu'on tape ;
  - pendant l'ouverture de session, une roue tourne à la place de la flèche ;
  - un mauvais mot de passe fait secouer le champ (oscillation amortie, 3 allers-retours en
    520 ms).
- **Fenêtres** (KWin) :
  - ouverture et fermeture en zoom (`scale`, de 0,9 à l'ouverture, jusqu'à 0,94 à la
    fermeture) ;
  - réduction en génie vers l'icône du Dock (`magiclamp`) ;
  - dialogues en feuille (`sheet`) ;
  - agrandissement animé (`maximize`).

Limites connues :

- KWin coupe ses animations de fenêtres quand le rendu est logiciel (llvmpipe). Dans la VM QEMU
  TCG, il n'y a donc ni zoom ni génie (`isEffectSupported magiclamp` = false). Ils fonctionnent
  sur une vraie carte graphique.
- Dans la VM, le compositeur met plusieurs secondes par image. L'enchaînement y est vérifié,
  pas la fluidité.
- Fichiers, Terminal, Kate et les autres apps restent des apps KDE. Elles suivent le thème
  (couleurs, Inter, décoration, animations de fenêtres, réglages Breeze dans `breezerc`), mais
  leurs widgets internes gardent les animations de Breeze.

## Cohérence des apps et des dialogues

- **Alertes du shell** (`Alerte.qml`), d'après le kit macOS 27 (« Alert », type Stacked) :
  - verre Large de 260 pt, rayon 34 ;
  - icône de 64 pt ;
  - titre Bold 13, message Regular 11 ;
  - boutons empilés en capsules de 28 pt (`Bouton.qml` : primaire, destructif, secondaire) ;
  - Retour lance l'action par défaut, Échap annule.
- **« À propos »** : une fenêtre du kit (fond opaque, rayon 16, ombre de fenêtre active, feux de
  14 pt).
- **Toutes les apps Qt/KDE** : style Kvantum `DropletClair` / `DropletSombre`, généré par
  `desktop/theme/render/kvantum.py` à partir des mesures du kit.
  - Contrôles de 24 pt, rayon 6.
  - Cases à cocher et boutons radio de 16 pt, curseur à bouton capsule de 20 × 16, barres de
    défilement en surimpression.
  - Menus de rayon 12, lignes survolées de rayon 8.
  - Onglets en contrôle segmenté.
  - Sélection et coches dans l'accent Droplet.
  - La bascule clair/sombre change aussi le thème Kvantum (pris en compte par les apps ouvertes
    ensuite).
- **Icônes** : thèmes `Droplet` / `Droplet-dark` (Breeze, LGPL-3.0). Seuls les dossiers sont
  recolorés dans le bleu Droplet (`icons_droplet.py`) ; sans cela, Breeze les peindrait dans
  l'accent rose.

Limites :

- Kvantum ne recharge pas son thème dans une app déjà ouverte.
- Le bouton par défaut des dialogues KDE est dessiné comme les autres boutons : Kvantum ne sait
  pas le remplir d'accent comme macOS.
- Les apps GTK (aucune n'est installée par défaut) ne suivent pas ce style.
- L'icône « Réseau » de la barre latérale garde la couleur d'accent : c'est une variante de
  dossier que le recoloriage ne couvre pas encore.
