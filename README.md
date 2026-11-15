# Ce qui sépare trois tailles d'un même modèle, c'est de savoir revenir

Un agent LLM joue le dilemme du prisonnier itéré contre Donnant-donnant, à trois
tailles du même modèle (Nemotron 3 : nano 30B, super 120B, ultra 550B). La
question de départ était : *est-ce que le gros modèle est plus gentil ?*

Non, et la question était mal posée. **Les trois tailles rendent les coups** :
trahies sans raison, elles ripostent toutes. Ce qui les sépare, c'est ce qui se
passe **après** : revenir à la coopération quand on a été puni.

![Probabilité de coopérer selon la situation, par taille de modèle](figures/reparation.png)

**Le plus petit lit parfaitement la partie, mais ne prévoit pas qu'un imitateur
pardonne — et quand on le lui dit, il revient.**

## Le résultat, en trois mesures

**1. Dans le même historique fabriqué, la réparation sépare les tailles.**
Chaque modèle est placé dans exactement la même situation et interrogé 30 fois.
Probabilité de coopérer au tour suivant, invite d'origine :

| situation | nano | super | ultra |
| --- | --- | --- | --- |
| trahi sans raison (riposter ?) | 0,00 | 0,07 | 0,00 |
| **puni après sa propre trahison** (revenir ?) | **0,13** | **0,87** | **1,00** |
| trahison mutuelle depuis 3 tours | 0,17 | 0,73 | 1,00 |
| son retour vient d'être exploité | 0,03 | 0,83 | 0,96 |

**2. Ça tient en parties complètes** (50 tours, Donnant-donnant) :

| palier | parties | ne trahit jamais | parties avec trahison qui finissent réparées | gain moyen/tour |
| --- | --- | --- | --- | --- |
| nano | 18 | 0 | **0 / 18** | 1,58 |
| super | 16 | 2 | **13 / 14** ¹ | 2,94 |
| ultra | 20 | 19 | 1 / 1 | 3,00 |

¹ La 14ᵉ trahit au tour 49 et est punie au tour 50 : la partie s'arrête avant
qu'elle puisse revenir. C'est l'horizon qui coupe, pas un refus.

**3. Le mécanisme.** Deux questions de compréhension, posées à part :

| | nano | super | ultra |
| --- | --- | --- | --- |
| « qu'a joué l'adversaire au dernier tour ? » | **1,00** | 1,00 | 1,00 |
| « que va-t-il jouer maintenant ? » quand la bonne réponse est *il me rend ma coopération* | **0,40** | 1,00 | 0,87 |

Puis l'intervention : on ajoute à l'invite *« Your opponent plays tit-for-tat »*.
Nano puni passe de **0,13 à 1,00**, piégé de 0,17 à 0,85, après une tentative
exploitée de 0,03 à 0,75.

Nano ne manque pas d'informations ; il manque d'un **modèle de l'adversaire**. Une
nuance qui n'est pas lissée : même quand il prévoit juste (0,73 des cas, puni), il
ne revient que 0,13 du temps. Prévoir ne suffit pas à le faire agir ; la règle
énoncée, si.

## Ce qui a été fait pour essayer de le casser

- **Retirer la sélection.** Dans une partie, un modèle qui ne trahit jamais n'est
  jamais puni : ultra n'a été puni qu'**une fois en 1 000 tours**, son « 100 % »
  initial était un seul coup. D'où les sondes d'état, où chaque taille reçoit le
  même historique.
- **Changer l'invite** (§6.5 du carnet). Quatre formulations : d'origine, objectif
  reformulé, options dans l'autre ordre, et des **étiquettes neutres A/B** sans
  le nom du jeu. L'écart de réparation survit aux quatre.
- **Une réserve qui est aussi un résultat.** En A/B, **nano trahit même en pleine
  paix** (0 sur 20, contre 0,80 avec les mots). Sa coopération de base est portée
  par le vocabulaire. Super et ultra ne bougent presque pas.
- **Lire les raisonnements.** Quand super ouvre en trahissant, il écrit que trahir
  est « *the dominant action* » et « *the safe answer* » : dominance et pire cas,
  pas « je teste sa réaction ».
- **Tester les mesures elles-mêmes** (`test_mesures.py`, 13 tests). L'un vérifie
  que l'invite des sondes est identique au caractère près à celle des parties ; un
  autre établit qu'**un temps de réparation d'un tour est un plancher mécanique**
  contre Donnant-donnant (revenir exige d'encaisser une fois le 0). Le temps ne
  pouvait donc pas distinguer les tailles ; le taux, si.

## Le défaut qui penchait du bon côté

La toute première exécution annonçait **96 % de coopération** pour nano. Le vrai
chiffre est **16 %**. À `max_tokens=600`, le raisonnement mangeait tout le budget,
l'API rendait `content: null`, et mon repli comptait ces tours comme « coopère ».

**Un coup non lu ne se devine pas.** Dans les parties, il fait échouer la partie ;
dans les sondes, il est enregistré illisible et **jamais retiré** — retirer serait
un second tirage, biaisé si l'illisibilité dépend du coup. `resultat_600jetons.json`
est gardé exprès, comme pièce.

## Ce que ça ne vaut pas

- **Un seul adversaire** (Donnant-donnant), **une seule famille de modèles**
  (Nemotron 3), **une seule température** (0,7). La phrase porte sur trois
  tailles d'une famille, pas sur « les LLM ».
- **Abandons.** 64 parties abandonnées en tout : 54 sur des pannes réseau
  (`getaddrinfo failed`, coupures), qui ne peuvent pas corréler avec l'issue
  d'une partie ; **10 sur deux coups illisibles de suite** (6 nano, 4 super). Même
  si les 6 parties nano manquantes avaient toutes réparé, nano serait à 6 sur 24
  contre 13 sur 14.
- **Les sondes coupent le raisonnement à 6 000 jetons** : 1 à 3 réponses
  illisibles par case chez ultra dans les situations profondes, exclues et
  comptées à part dans `analyse_sondes.py`.
- **Aucun classement de modèles, et il n'y en aura pas.** Le dépôt voisin a établi
  que les palmarès dépendent du plateau.

## Ce que ça coûte

| | appels | coût |
| --- | --- | --- |
| parties complètes (54) | ~2 700 | 1,96 $ |
| sondes d'état | 1 838 | 3,90 $ |

Le coût d'un tour est porté par la délibération, pas par le jeu : la réponse fait
un mot, le raisonnement des centaines à des milliers de jetons (médianes mesurées
dans les sondes : nano 636, super 734, ultra 1 471).

## Les témoins viennent du dépôt voisin

[`Yoh5/tit-for-tat`](https://github.com/Yoh5/tit-for-tat) est le tournoi
déterministe de référence : Pavlov se relève d'un accident en 2 à 3 tours, là où
deux Donnant-donnant ne se relèvent pas dans 76 à 79 % des cas. La matrice de
gains est **importée** de ce dépôt, jamais recopiée.

## Faire tourner

Les deux dépôts voisins sont attendus à côté de celui-ci (`AI_RACINE` permet de
les ranger ailleurs) :

```
un-dossier/
├── tit-for-tat/        github.com/Yoh5/tit-for-tat   (matrice et stratégies)
├── glassbox/           github.com/Yoh5/glassbox      (client Nebius, compteurs d'usage)
└── tit-for-tat-llm/    ce dépôt
```

```bash
export NEBIUS_API_KEY=...          # set NEBIUS_API_KEY=... sous Windows

python reparation.py --repetitions 20                       # parties complètes
python sondes_etats.py --variantes base --n 30              # sondes d'état
python sondes_etats.py --variantes lettres objectif ordre   # robustesse de l'invite
python sondes_etats.py --variantes q_dernier q_prediction   # compréhension
python sondes_etats.py --variantes indice                   # l'intervention
python analyse_sondes.py                                    # tous les tableaux
python figure_reparation.py                                 # la figure (matplotlib)
python -m pytest test_mesures.py                            # les mesures testées
```

Chaque partie et chaque tirage sont écrits dès qu'ils finissent
(`reparation.jsonl`, `sondes_etats.jsonl`) : une coupure ne redépense rien, et
relancer reprend où on s'était arrêté. Toutes les figures et tous les tableaux
sont recalculés depuis ces deux fichiers.

## Le carnet

`RECHERCHE.md` est le carnet de recherche : l'hypothèse de départ réfutée et
déclarée telle, la variable recadrée deux fois, et la campagne complète au §8.
C'est la partie de ce dépôt que je lirais d'abord.

## Licence

Apache-2.0. Voir `LICENSE`.
