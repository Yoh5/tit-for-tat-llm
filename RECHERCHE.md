# Points de recherche — agents LLM dans le dilemme du prisonnier itéré

Carnet ouvert le 22/10/2026. Chaque entrée dit **ce qu'on a vu**, **ce que ça
vaut** (une sonde n'est pas un résultat) et **ce qu'il faudrait pour que ça en
devienne un**. Rien ici n'est publiable tant que la colonne « ce qu'il
faudrait » n'est pas faite.

Protocole commun : 50 tours, longueur fixe, aucun bruit, adversaire
Donnant-donnant, température 0,7, invite identique, graine 1.
**Une seule exécution par palier.**

---

## 1. L'hypothèse de départ est réfutée

J'avais proposé : *le tour de la première trahison monte avec la taille du
modèle.* Faux, et le milieu de l'échelle le dit le plus fort.

| palier | 1re trahison | retours | coop. | gain/tour |
|---|---|---|---|---|
| nano | tour **9** | 0 | 16 % | 1,40 |
| super | tour **1** | **2** | 96 % | 2,96 |
| ultra | **jamais** | — | 100 % | 3,00 |

Le **gain** monte bien avec le palier. Le **tour de la première trahison**,
non : 9, puis 1, puis jamais. Un classement monotone à droite, non monotone
au milieu : la variable que je croyais mesurer n'existe pas.

Seul ultra satisfait le critère d'Axelrod « ne trahis jamais le premier ».

## 2. La vraie variable est la réparation, pas la gentillesse

```
nano  : CCCCCCCCDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD
super : DCCCCCCCCCCCCCCDCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
ultra : CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
```

nano et super échouent tous deux au critère « ne trahis pas le premier ». Ce
qui les sépare, c'est ce qui se passe **après la riposte**. nano s'enferme dans 41 tours de trahison mutuelle. super se fait
punir au tour 2, revient au tour 3, recommence au tour 16, revient au tour 18.

L'écart de gain — **1,40 contre 2,96, soit plus du double** — vient
entièrement de là.

**Ce que ça vaut :** deux exécutions, une graine, un adversaire. L'effet est
énorme, ce qui est encourageant et suspect à la fois.

**Ce qu'il faudrait :** 20 répétitions par palier avec des graines
différentes, et la distribution du nombre de retours plutôt que le chiffre
d'une partie. Mesure proposée : **le temps de réparation** — nombre de tours
entre la riposte de l'adversaire et le retour à la coopération mutuelle.
C'est l'analogue exact de la mesure Pavlov de la section 5 du dépôt voisin
(2 tours sous bruit d'exécution, 3 sous bruit de perception), donc le
plateau existant fournit déjà les témoins.

## 3. Pourquoi super trahit-il au tour 1 ?

Au tour 1 il n'y a pas d'historique : l'invite dit littéralement « No rounds
played yet ». Trahir là n'est pas une réponse à quoi que ce soit, c'est une
**ouverture**. Deux lectures possibles, et elles ne se distinguent pas avec
une seule partie :

- il sonde, pour voir à qui il a affaire — comportement de Sondeur (Joss),
  qui est déjà sur le plateau du dépôt voisin ;
- il applique une récurrence à l'envers (« trahir domine au coup unique »)
  sans voir que le jeu est répété.

**Ce qu'il faudrait :** lire les raisonnements. Le client Nebius jette le
champ `reasoning` quand `content` existe. Le garder et classer les
justifications du tour 1 séparerait les deux lectures — et un agent qui écrit
« je teste sa réaction » n'est pas le même objet qu'un agent qui écrit
« trahir est dominant ».

## 4. Le repli silencieux (déjà consigné dans NOTES.md)

À `max_tokens=600`, 23 tours sur 50 revenaient sans contenu et mon repli les
comptait comme « coopère » : la sonde annonçait 96 % de coopération pour nano
au lieu de 16 %. **Le défaut penchait du côté flatteur.**

**Règle :** un coup non lu ne se devine pas. Et le budget de jetons doit être
dimensionné **par palier**, parce qu'il dépend de la longueur du raisonnement,
pas de celle de la réponse — qui fait un mot.

## 5. Ce que ça coûte, mesuré

| palier | $/tour | latence médiane | 50 tours |
|---|---|---|---|
| nano | 0,000133 | 1,7 s | 0,0066 $ |
| super | 0,000866 | **9,5 s** | 0,0433 $ |
| ultra | 0,001254 | 1,3 s | 0,0627 $ |

**Le coût d'un tour est porté par la délibération, pas par le jeu** : la
réponse fait un mot, le raisonnement fait des milliers de caractères.

Et il y a une bosse au milieu. En divisant le rapport de coût mesuré par le
rapport de prix catalogue des jetons de sortie, on estime les jetons
réellement consommés : super en consomme **1,7 fois plus que nano**, et ultra
**0,43 fois ce que consomme super** — moins que nano en valeur relative
(x0,75). La latence dit la même chose : 9,5 s pour super contre 1,3 s pour
ultra, et 537 s contre 76 s sur la partie entière.

**Le modèle du milieu est celui qui délibère le plus.** Le plus gros tranche
vite. Et c'est aussi celui du milieu qui sonde puis répare, tandis que le plus
gros coopère sans jamais rien essayer. Les deux observations vont ensemble et
demandent la même vérification.

> Estimation, pas mesure : elle suppose que la part des jetons d'entrée est
> négligeable et que les rapports entrée/sortie se compensent. **À
> remplacer** par les vrais compteurs : `nebius_call` calcule le coût depuis
> le bloc `usage` puis le jette. Lui faire rendre `prompt_tokens` et
> `completion_tokens` est un changement d'une ligne, et ça transforme cette
> section d'une inférence en une mesure.

## §6.1 REPONDUE — 31/10/2026, 41 parties completes, 1,62 $

Le protocole annonce a ete execute : trois paliers, 20 repetitions visees,
50 tours, `reparation.py`. Chaque partie est ecrite des qu'elle finit, donc
une coupure ne redepense rien — et il y en a eu.

### Ce qu'on a vu

| palier | parties completes | 1re trahison | gain/tour |
|---|---|---|---|
| nano | 12 | mediane tour 8, **0/12 ne trahit jamais** | 1,593 |
| super | 9 | mediane tour 14, 1/9 jamais | 2,956 |
| ultra | 20 | **19/20 ne trahissent jamais** | 2,999 |

Et la mesure qui etait le but :

| palier | episodes de riposte | repares | **censures** | taux de reparation | duree mediane |
|---|---|---|---|---|---|
| nano | 14 | 2 | **12** | **14 %** | 1 tour |
| super | 9 | 9 | 0 | **100 %** | 1 tour |
| ultra | 1 | 1 | 0 | 100 % | 1 tour |

### Ce que ca vaut

**L'hypothese de §2 tient, et se precise.** Ce n'est pas la gentillesse qui
separe les paliers : nano trahit **plus tot** que super (tour 8 contre 14) et
gagne pourtant moitie moins. C'est la reparation.

**Mais la variable n'est pas la VITESSE de reparation, c'est son EXISTENCE.**
Les trois paliers qui reparent le font en **un tour**, mediane identique. Ce
qui change est le taux : 14 % contre 100 %. §2 proposait de mesurer un *temps*
de reparation ; le temps ne distingue rien, le taux distingue tout. La
formulation « combien de tours met-il a rentrer » etait la mauvaise question,
et il a fallu la mesurer pour le voir.

### Ce qu'il faudrait encore

**L'echantillon n'est pas celui qui etait prevu** : 12, 9 et 20 parties au lieu
de 20 partout. **40 parties ont ete abandonnees**, et la repartition decide si
c'est grave :

- **32 sur 40 (80 %) sont mortes au tour 0**, avant le moindre coup, sur
  `getaddrinfo failed` — la pile reseau de la machine, pas les modeles. Une
  panne qui survient avant que la partie existe ne peut pas correler avec son
  issue.
- 5 sont des coupures reseau en cours de partie.
- **3 sont de vrais echecs de lecture**, tous sur nano, aux tours 19, 22 et 39 :
  deux coups illisibles de suite malgre 2 000 jetons. C'est le seul biais
  possible, et il va dans un sens precis — si le raisonnement de nano s'allonge
  quand l'historique grossit, ce sont ses parties **les plus difficiles** qui
  manquent. Trois parties ne retournent pas un ecart de 14 % contre 100 %,
  mais il faut l'ecrire.

**Avant de publier :** refaire les paliers nano et super sur un reseau stable
pour atteindre 20 parties completes chacun, et **dimensionner le budget de
jetons de nano par la longueur de l'historique**, pas par une constante.

### Deux corrections d'une ligne, faites

`glassbox.nebius.nebius_call` accepte desormais `on_usage` : les compteurs
`prompt_tokens` / `completion_tokens` et le `finish_reason`, qui etaient
calcules en cout puis jetes, sont exposes. La section 5 peut passer d'une
inference a une mesure. Et **le champ `reasoning` est capte** : le
raisonnement du tour 1 est enregistre dans chaque partie, donc §3 — distinguer
l'agent qui sonde de celui qui applique « trahir domine » — devient lisible
plutot qu'hypothetique. Signature inchangee, 329 tests de glassbox passent.

## 6. Questions ouvertes, par ordre de rapport

1. **Le temps de réparation en fonction du palier** (§2). La courbe que
   personne n'a publiée. Coût estimé : 20 répétitions x 3 paliers x 50 tours
   = 3 000 appels, soit ~2 $.
2. **Deux LLM l'un contre l'autre.** Se reconnaissent-ils ? Le dépôt voisin a
   déjà le témoin chiffré de la coalition de Southampton (récolteur 3,268,
   donnant-donnant dixième) — la question « deux instances du même modèle
   forment-elles une coalition sans qu'on le leur demande » a donc une
   référence.
3. **Sous bruit.** Le dépôt voisin montre que Donnant-donnant se suicide sous
   bruit. Un agent qui répare devrait, lui, y survivre — c'est la prédiction
   la plus nette qu'on puisse tirer de §2, donc celle qu'il faut essayer de
   casser en premier.
4. **Le budget de persuasion.** Combien de jetons de contexte adverse pour
   retourner un agent coopératif, et est-ce que ce coût monte avec le palier.
   C'est le pont avec le banc d'essai adverse.
5. **L'invite est-elle le résultat ?** « Maximise your own total score » est
   une consigne forte. Changer un mot peut tout déplacer. Avant de publier
   quoi que ce soit, il faut montrer que l'effet survit à trois formulations.

## 7. Ce qui serait publiable, et ce qui ne l'est pas

Publiable une fois §2 répété : *« Entre deux tailles du même modèle, ce qui
change n'est pas de trahir moins, c'est de savoir rentrer. »* Un graphique,
un protocole, un dépôt rejouable.

Pas publiable : tout classement « quel modèle est le plus coopératif ». Le
dépôt voisin a déjà établi que les classements dépendent du plateau — publier
un palmarès de modèles reproduirait exactement l'erreur que ce travail
dénonce.

## 8. Campagne du 14-15/11/2026 — la sélection retirée, le mécanisme isolé

Coût de la campagne : **~4,3 $** (sondes 3,90 $, parties 0,34 $). Données :
`sondes_etats.jsonl` (2 038 appels), `reparation.jsonl` (parties). Analyse :
`python analyse_sondes.py`. Tests des mesures : `python -m pytest test_mesures.py`
(13 tests).

### 8.1 Un défaut de construction des parties, et ce qu'il cachait

Dans une partie, **un palier qui ne trahit jamais n'entre jamais dans la
situation qu'on veut mesurer**. Ultra a joué 1 000 tours et n'a été puni qu'une
fois : son « 100 % de réparation » de §6.1 était **un seul coup**. Et nano n'est
observé puni qu'après des trahisons qu'il a choisies.

Deux réponses :
- **réanalyser les parties en stratégie à mémoire d'un coup**, P(coopérer | état
  du tour précédent), la mesure standard de la théorie des jeux ;
- **les sondes d'état** (`sondes_etats.py`) : chaque palier placé dans le **même
  historique fabriqué**, échantillonné N fois. Plus de sélection. Un coup
  illisible y est enregistré illisible, **jamais retiré** : retirer serait un
  second tirage, biaisé si l'illisibilité dépend du coup.

### 8.2 La réplication en parties complètes tient

Après correction d'une panne (les parties mouraient au premier `getaddrinfo
failed` ; `reparation.avec_reprise` réessaie désormais le **réseau seulement**) :

| palier | parties | parties avec trahison qui finissent réparées | P(C) après C/D | P(C) après D/D |
|---|---|---|---|---|
| nano | 18 | **0 / 18** | 4/27 = 0,15 | **12/626 = 0,02** |
| super | 16 | **14 / 14** ¹ | 18/22 = 0,82 | 9/13 = 0,69 |
| ultra | 20 | 1 / 1 | 1/1 | jamais observé |

¹ Une partie super est comptée « censurée » par la mesure : trahison au tour 49,
punition au tour 50, **fin de partie**. C'est l'horizon qui coupe, pas un refus.

Sur les parties de §6.1 seules, nano 0/12 contre super 8/8 : test exact de Fisher
**p = 8·10⁻⁶**.

**Constat de mesure** (`test_un_tour_est_le_minimum_contre_donnant_donnant`) :
contre Donnant-donnant, rentrer exige d'encaisser **une fois** le 0. Un temps de
réparation de 1 tour est donc un **plancher mécanique**. §6.1 avait raison de dire
que le temps ne distingue rien, et c'était en partie par construction.

### 8.3 Les sondes d'état : le palier se confirme, et ultra est enfin mesuré

Invite de base (identique au caractère près à celle des parties, testé). P(coopérer),
IC 95 % de Wilson, 30 tirages par case :

| état fabriqué | nano | super | ultra |
|---|---|---|---|
| ouverture | 0,97 | 0,90 | 1,00 |
| 10 tours de paix | 0,80 | 1,00 | 1,00 |
| **victime** d'une trahison gratuite | 0,00 | 0,07 | **0,00** |
| **puni** (je reviens après avoir trahi) | **0,13** [0,05–0,30] | **0,87** [0,70–0,95] | **1,00** [0,88–1,00] |
| piégé 1 tour | 0,40 | 0,86 | 1,00 |
| piégé 3 tours | 0,17 | 0,73 | 1,00 |
| piégé 8 tours | 0,13 | 0,63 | 1,00 |
| **tentative** de retour exploitée | **0,03** | 0,83 | 0,96 |

- **Ultra sait réparer** (29/29), ce que les parties ne pouvaient pas montrer.
- **Ultra n'est pas un naïf** : trahi gratuitement, il riposte 29 fois sur 29. Les
  trois paliers rendent les coups ; ce qui les sépare est **l'après**.
- **Le piège s'approfondit** : plus la trahison mutuelle dure, moins on en sort
  (nano 0,40 → 0,13, super 0,86 → 0,63). Ultra ne bouge pas.

### 8.4 L'invite n'est pas le résultat (§6.5) — sauf pour nano en paix

| variante | ce qui change | nano puni | super puni | ultra puni |
|---|---|---|---|---|
| base | — | 0,13 | 0,87 | 1,00 |
| objectif | « Your goal is to end the game with as many points as you can » | 0,13 | 0,93 | 1,00 |
| ordre | DEFECT annoncé avant COOPERATE | 0,20 | 1,00 | 1,00 |
| **lettres** | A / B, « a repeated two-player game » : ni mots chargés ni nom du jeu | **0,00** | 0,89 | 1,00 |

**L'écart de réparation survit aux quatre formulations.** Mais les étiquettes
neutres révèlent autre chose : **nano trahit en pleine paix** (0/20, contre 0,80
avec les mots) et à l'ouverture (0,20 contre 0,97). **Sa coopération de base est
portée par le vocabulaire**, pas par un calcul. Super (paix 0,85) et ultra (1,00)
ne bougent presque pas. À écrire tel quel : c'est une réserve, et c'est un
résultat.

### 8.5 Le mécanisme : nano voit, mais ne prévoit pas le pardon

Questions de compréhension, sur l'invite de base, 15 tirages ; la case donne le
taux de **bonnes** réponses :

| question | état | nano | super | ultra |
|---|---|---|---|---|
| qu'a joué l'adversaire au dernier tour ? | les trois | **1,00** | 1,00 | 1,00 |
| que va-t-il jouer maintenant ? (réponse : il trahit encore) | piégé 3 | 1,00 | 1,00 | 1,00 |
| idem (réponse : **il me rend ma coopération**) | puni | 0,73 | 0,93 | 1,00 |
| idem (réponse : **il me rend ma coopération**) | tentative | **0,40** | 1,00 | 0,87 |

Et l'**intervention** : on dit à l'agent « *your opponent plays tit-for-tat* ».

| état | nano sans | **nano avec l'indice** | super sans | super avec |
|---|---|---|---|---|
| puni | 0,13 | **1,00** | 0,87 | 1,00 |
| piégé 3 | 0,17 | **0,85** | 0,73 | 1,00 |
| tentative | 0,03 | **0,75** | 0,83 | 1,00 |

**Lecture.** Nano lit l'historique sans erreur. Il échoue à **prévoir qu'un
imitateur rend la coopération** : il prédit que l'adversaire continuera ce qu'il
vient de faire. Quand on lui donne la règle, il répare. **Son échec n'est pas la
tentation, c'est le modèle de l'adversaire.**

**La nuance à ne pas lisser** : même quand nano prévoit juste (0,73 sur « puni »),
il ne revient que 0,13 du temps. Sa propre prévision ne suffit pas à le faire
agir ; la règle **énoncée** le fait. Deux défauts, donc : il prévoit mal, et il
n'agit pas sur ce qu'il prévoit. Les tirages des deux questions sont
indépendants : ce n'est pas une corrélation au niveau de la réponse.

### 8.6 §3 répondu : super n'ouvre pas en sondant

Les deux ouvertures par trahison de super (parties 2 et 7) écrivent « *the dominant
action each stage is defect* » et « *safe answer is defect* » : **dominance au coup
unique et pire cas**, pas « je teste sa réaction ». C'est la seconde lecture de §3.

### 8.7 Ce qui reste fragile, dit avant qu'on le trouve

- **Un seul adversaire** (Donnant-donnant) et **une seule famille de modèles**
  (Nemotron 3) : la phrase publiable porte sur trois tailles d'une famille.
- **Abandons pour coup illisible deux fois** : 6 parties nano, 4 super, à 2 000
  jetons. Même si les 6 parties nano manquantes avaient toutes réparé, nano serait
  à 6/24 contre 14/14.
- **Les sondes coupent le raisonnement à 6 000 jetons** : 1 à 3 coups illisibles
  par case chez ultra dans les états profonds, exclus et comptés à part.
- Température 0,7 partout ; non testée ailleurs.

### 8.8 La phrase publiable, révisée

*Entre trois tailles d'un même modèle, toutes rendent les coups ; ce qui change est
de savoir rentrer. Le plus petit lit parfaitement la partie mais ne prévoit pas
qu'un imitateur pardonne — et quand on le lui dit, il rentre.*
