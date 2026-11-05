# Sonde : un agent LLM dans le dilemme du prisonnier itéré

Extension de `../tit-for-tat/`. **Rien ici n'est publiable en l'état** : c'est
une sonde jetable du 22/10/2026, un seul duel, un seul modèle, une seule
graine. Elle répond à deux questions, et seulement à celles-là — combien ça
coûte, et est-ce que l'agent tient la coopération.

## Ce qu'elle a trouvé

**Nemotron-3-Nano, à qui on demande de maximiser son propre total, coopère
huit tours, trahit le premier au tour 9, et ne répare jamais.**

```
LLM : CCCCCCCCDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD
DD  : CCCCCCCCCDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD
```

Donnant-donnant riposte au tour 10, et les deux restent bloqués 41 tours à
1 point. Zéro tentative de retour à la coopération.

| | gain par tour |
|---|---|
| LLM (nano) | 1,40 |
| Donnant-donnant | 1,30 |

À comparer au plateau du dépôt voisin : la **dernière** des gentilles y marque
2,420 et la **première** des autres 2,329. Cet agent est sous les deux.
C'est la première fois qu'on a un joueur qui tombe dans la famille « trahit
le premier » sans avoir été écrit pour.

Coût : **0,0066 $ pour 50 tours**, 94 s, palier `nano`.

## Le piège, qui vaut autant que le résultat

La **première** exécution annonçait **96 % de coopération et 2,96 par tour** —
l'inverse. Elle était fausse, et silencieusement.

`max_tokens=600` : Nemotron raisonne avant de répondre, le raisonnement
consommait tout le budget (2 400 à 2 600 caractères), l'API rendait
`content: null` avec `finish_reason=length`, et le repli de la sonde comptait
ces tours-là comme « coopère ». **23 tours sur 50.** Le taux de coopération
mesurait donc surtout mon propre repli.

À 2 000 jetons : 0 illisible, et le résultat s'inverse.

C'est exactement la faute que le dépôt voisin raconte en section 5 — une
mesure sans échantillon rendue comme un zéro. Ici le repli était pire qu'un
zéro : il penchait du côté flatteur.

**À corriger avant toute vraie campagne** : un tour dont le coup n'est pas lu
ne doit pas être joué par défaut, il doit faire échouer le duel ou être
rapporté à part. Jamais être deviné.

## Ce que coûterait la vraie expérience

0,000133 $ par tour, mesuré. Le tournoi du dépôt voisin fait 9 stratégies,
200 tours d'espérance, 20 répétitions. Un joueur LLM contre tout le plateau :
environ 10 duels x 200 x 20 = 40 000 appels, soit **~5,3 $ par graine**, et
~64 $ pour les douze graines qui servent déjà à montrer que le vainqueur
n'est pas stable. Abordable, mais à ne pas lancer sans avoir réglé le point
précédent.

## Les fichiers

| | |
|---|---|
| `sonde_llm.py` | la sonde ; `--tours`, `--jetons`, `--palier` |
| `resultat_600jetons.json` | l'exécution fausse, gardée exprès comme pièce |
| `resultat_2000jetons.json` | l'exécution propre |

Clé lue dans `../glassbox/.env`, client Nebius réutilisé de Glass Box (il
calcule le coût depuis le bloc `usage` de l'API, pas depuis une estimation).
Gains importés de `../tit-for-tat/strategies.py`, jamais recopiés.
