# Ce qui sépare deux tailles d'un même modèle, c'est la réparation

Un agent LLM joue le dilemme du prisonnier itéré contre Donnant-donnant, à trois
tailles du même modèle. La question de départ était : *est-ce que le gros modèle
est plus gentil ?*

Réponse : non, et la question était mal posée. Le petit modèle trahit **plus
tôt** que le moyen, et gagne pourtant moitié moins. Ce qui les sépare n'est pas
de trahir moins, c'est de **savoir rentrer** après avoir été puni.

| palier | parties | 1re trahison (médiane) | ne trahit jamais | gain/tour | **répare** |
| --- | --- | --- | --- | --- | --- |
| nano | 12 | tour **8,5** | 0/12 | 1,593 | **14 %** (2 épisodes sur 14) |
| super | 9 | tour **14,5** | 1/9 | 2,956 | **100 %** (9 sur 9) |
| ultra | 20 | tour 8 (une seule) | **19/20** | 2,999 | 100 % (1 sur 1) |

41 parties complètes, 50 tours chacune, **1,62 $ d'appels mesurés**. Les trois
paliers qui réparent le font en une médiane d'**un tour** : le *temps* de
réparation ne distingue rien, le *taux* distingue tout.

C'était l'erreur de formulation du carnet, et il a fallu la mesurer pour la
voir. §6.1 de `RECHERCHE.md` proposait de mesurer « combien de tours met-il à
rentrer » ; la bonne question était « rentre-t-il ».

## Le défaut qui penchait du bon côté

La première exécution annonçait **96 % de coopération** pour nano. Le vrai
chiffre est **16 %**.

À `max_tokens=600`, le modèle raisonne avant de répondre, la réflexion mangeait
tout le budget, l'API rendait `content: null` avec `finish_reason=length`, et mon
repli comptait ces tours comme « coopère ». 23 tours sur 50. À 2 000 jetons :
zéro illisible, et le résultat s'inverse.

**Un coup non lu ne se devine pas.** Il fait échouer la partie, ou il se
rapporte à part — jamais un défaut qui penche du côté flatteur.
`resultat_600jetons.json` est gardé dans le dépôt exprès, comme pièce.

Et le budget de jetons se dimensionne **par palier**, parce qu'il dépend de la
longueur du raisonnement, pas de celle de la réponse — qui fait un mot.

## Ce que ça coûte, et où part l'argent

| palier | $/tour | latence médiane | 50 tours |
| --- | --- | --- | --- |
| nano | 0,000133 | 1,7 s | 0,0066 $ |
| super | 0,000866 | **9,5 s** | 0,0433 $ |
| ultra | 0,001254 | 1,3 s | 0,0627 $ |

**Le coût d'un tour est porté par la délibération, pas par le jeu.** Et il y a
une bosse au milieu : le modèle moyen est celui qui délibère le plus, le plus
gros tranche vite. C'est aussi celui du milieu qui sonde puis répare, tandis que
le plus gros coopère sans jamais rien essayer. Les deux observations vont
ensemble.

## Ce que ça ne vaut pas encore

L'écart de 14 % à 100 % est énorme, ce qui est encourageant **et** suspect. Ce
qui manque, dit avant qu'on me le demande :

- **L'échantillon n'est pas celui qui était prévu** : 12, 9 et 20 parties au
  lieu de 20 partout. **40 parties ont été abandonnées**, et la répartition
  décide si c'est grave :
  - **32 sur 40 sont mortes au tour 0**, avant le moindre coup, sur
    `getaddrinfo failed` — la pile réseau de la machine, pas les modèles. Une
    panne qui survient avant que la partie existe ne peut pas corréler avec son
    issue.
  - 5 sont des coupures réseau en cours de partie.
  - **3 sont de vrais échecs de lecture**, tous sur nano, aux tours 19, 22 et
    39. C'est le seul biais possible, et il va dans un sens précis : si le
    raisonnement de nano s'allonge quand l'historique grossit, ce sont ses
    parties **les plus difficiles** qui manquent. Trois parties ne retournent
    pas un écart de 14 % contre 100 %, mais il faut l'écrire.
- **Un seul adversaire** (Donnant-donnant), **une seule invite**. « Maximise
  your own total score » est une consigne forte ; changer un mot peut tout
  déplacer. L'effet doit survivre à trois formulations avant de valoir un
  article.
- **Aucun classement de modèles ici, et il n'y en aura pas.** Le dépôt voisin a
  établi que les palmarès dépendent du plateau ; publier « quel modèle est le
  plus coopératif » reproduirait exactement l'erreur que ce travail dénonce.

## Les témoins viennent du dépôt voisin, pas d'ici

[`Yoh5/tit-for-tat`](https://github.com/Yoh5/tit-for-tat) est le tournoi
déterministe qui sert de référence : Pavlov se relève d'un accident en 2 tours
quand le coup a dérapé et 3 quand il a été mal perçu, là où deux Donnant-donnant
ne se relèvent pas dans 76 à 79 % des cas. C'est contre ces chiffres-là que
« réparer » veut dire quelque chose.

La matrice de gains est **importée** de ce dépôt, jamais recopiée : si elle
change là-bas, elle change ici.

## Faire tourner

Les deux dépôts voisins sont attendus à côté de celui-ci :

```
un-dossier/
├── tit-for-tat/        github.com/Yoh5/tit-for-tat   (matrice et stratégies)
├── glassbox/           github.com/Yoh5/glassbox      (client Nebius, compteurs d'usage)
└── tit-for-tat-llm/    ce dépôt
```

`AI_RACINE` permet de les ranger ailleurs. La clé se lit dans
l'environnement — rien ici ne lit un `.env` suivi par git :

```bash
export NEBIUS_API_KEY=...        # set NEBIUS_API_KEY=... sous Windows

python sonde_llm.py --tours 50                   # une partie, un palier, pour voir le coût
python reparation.py --repetitions 20            # §6.1 : le taux de réparation par palier
python experience_bruit.py --palier nano --bruit 0.1 --graines 1,2 --tours 40
```

Python 3.10 ou plus, et aucune dépendance hors bibliothèque standard de ce côté.

`reparation.py` écrit chaque partie dès qu'elle finit, dans
`reparation.jsonl` : une coupure ne redépense rien. Il y en a eu 37.

## Le carnet

`RECHERCHE.md` est le carnet de recherche, en français — l'hypothèse de départ
réfutée et déclarée telle, la variable recadrée, les six questions ouvertes
classées par rapport, et la frontière explicite entre ce qui serait publiable et
ce qui ne l'est pas. Chaque entrée dit ce qu'on a vu, ce que ça vaut, et ce qu'il
faudrait pour que ça en devienne un résultat.

C'est la partie de ce dépôt que je lirais d'abord.

## Licence

Apache-2.0. Voir `LICENSE`.
