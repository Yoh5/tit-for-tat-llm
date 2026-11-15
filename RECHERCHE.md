# Research notes — LLM agents in the iterated prisoner's dilemma

> **En bref (français).** Carnet de recherche ouvert le 22/10/2026. L'hypothèse
> de départ (« le plus gros modèle trahit plus tard ») est réfutée (§1). La vraie
> variable est la **réparation** : revenir à la coopération après avoir été puni
> (§2), et c'est son **taux** qui sépare les tailles, pas sa durée (§6.1). La
> campagne du 14-15/11 (§8) retire le biais de sélection des parties en plaçant
> chaque taille dans le même historique fabriqué : 0,13 / 0,87 / 1,00. L'écart
> survit à quatre variantes de l'invite ; le plus petit modèle lit bien la partie
> mais ne prévoit pas le pardon, et répare quand on lui donne la règle. Les
> limites sont écrites en §8.7.

Notebook opened on 22/10/2026. Each entry says **what was seen**, **what it is
worth** (a probe is not a result) and **what it would take for it to become
one**. Nothing here is publishable until the "what it would take" column is done.

Common protocol: 50 rounds, fixed length, no noise, tit-for-tat opponent,
temperature 0.7, identical prompt, seed 1.
**A single run per tier.**

---

## 1. The starting hypothesis is refuted

I had proposed: *the round of the first defection rises with model size.* False,
and the middle of the scale says so the loudest.

| tier | 1st defection | returns | coop. | payoff/round |
|---|---|---|---|---|
| nano | round **9** | 0 | 16% | 1.40 |
| super | round **1** | **2** | 96% | 2.96 |
| ultra | **never** | — | 100% | 3.00 |

The **payoff** does rise with the tier. The **round of the first defection** does
not: 9, then 1, then never. A ranking that is monotone on the right, non-monotone
in the middle: the variable I thought I was measuring does not exist.

Only ultra meets Axelrod's criterion "never defect first".

## 2. The real variable is repair, not niceness

```
nano  : CCCCCCCCDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD
super : DCCCCCCCCCCCCCCDCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
ultra : CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
```

nano and super both fail the "don't defect first" criterion. What separates
them is what happens **after the retaliation**. nano locks itself into 41 rounds
of mutual defection. super gets punished on round 2, comes back on round 3,
starts again on round 16, comes back on round 18.

The payoff gap — **1.40 against 2.96, more than double** — comes entirely from
there.

**What it is worth:** two runs, one seed, one opponent. The effect is huge,
which is encouraging and suspicious at the same time.

**What it would take:** 20 repetitions per tier with different seeds, and the
distribution of the number of returns rather than the figure from one game.
Proposed measure: **repair time** — number of rounds between the opponent's
retaliation and the return to mutual cooperation. It is the exact analogue of
the Pavlov measure in section 5 of the sibling repository (2 rounds under
execution noise, 3 under perception noise), so the existing field already
provides the baselines.

## 3. Why does super defect on round 1?

On round 1 there is no history: the prompt literally says "No rounds played
yet". Defecting there is not a response to anything, it is an **opening**. Two
possible readings, and they cannot be told apart with a single game:

- it probes, to see who it is dealing with — Tester (Joss) behaviour, which is
  already in the sibling repository's field;
- it applies backward induction ("defecting dominates in the one-shot game")
  without seeing that the game is repeated.

**What it would take:** reading the reasoning. The Nebius client discards the
`reasoning` field when `content` exists. Keeping it and classifying the round-1
justifications would separate the two readings — and an agent that writes
"I'm testing its reaction" is not the same object as an agent that writes
"defecting is dominant".

## 4. The silent fallback (already recorded in NOTES.md)

At `max_tokens=600`, 23 rounds out of 50 came back with no content and my
fallback counted them as "cooperate": the probe reported 96% cooperation for
nano instead of 16%. **The bug leaned the flattering way.**

**Rule:** an unread move is not guessed. And the token budget must be sized
**per tier**, because it depends on the length of the reasoning, not of the
answer — which is one word.

## 5. What it costs, measured

| tier | $/round | median latency | 50 rounds |
|---|---|---|---|
| nano | 0.000133 | 1.7 s | $0.0066 |
| super | 0.000866 | **9.5 s** | $0.0433 |
| ultra | 0.001254 | 1.3 s | $0.0627 |

**The cost of a round is carried by deliberation, not by the game**: the answer
is one word, the reasoning thousands of characters.

And there is a bump in the middle. Dividing the measured cost ratio by the
catalogue price ratio of output tokens estimates the tokens actually consumed:
super consumes **1.7 times as many as nano**, and ultra **0.43 times what super
consumes** — less than nano in relative terms (x0.75). Latency says the same:
9.5 s for super against 1.3 s for ultra, and 537 s against 76 s over the whole
game.

**The middle model is the one that deliberates the most.** The biggest one
decides fast. And it is also the middle one that probes then repairs, while the
biggest cooperates without ever trying anything. The two observations go
together and call for the same check.

> Estimate, not measurement: it assumes the share of input tokens is negligible
> and that input/output ratios cancel out. **To be replaced** by the real
> counters: `nebius_call` computes the cost from the `usage` block then discards
> it. Making it return `prompt_tokens` and `completion_tokens` is a one-line
> change, and it turns this section from an inference into a measurement.

## §6.1 ANSWERED — 31/10/2026, 41 complete games, $1.62

The announced protocol was run: three tiers, 20 repetitions targeted, 50 rounds,
`reparation.py`. Each game is written as soon as it finishes, so an interruption
re-spends nothing — and there were some.

### What was seen

| tier | complete games | 1st defection | payoff/round |
|---|---|---|---|
| nano | 12 | median round 8, **0/12 never defect** | 1.593 |
| super | 9 | median round 14, 1/9 never | 2.956 |
| ultra | 20 | **19/20 never defect** | 2.999 |

And the measure that was the goal:

| tier | retaliation episodes | repaired | **censored** | repair rate | median duration |
|---|---|---|---|---|---|
| nano | 14 | 2 | **12** | **14%** | 1 round |
| super | 9 | 9 | 0 | **100%** | 1 round |
| ultra | 1 | 1 | 0 | 100% | 1 round |

### What it is worth

**The §2 hypothesis holds, and sharpens.** It is not niceness that separates
the tiers: nano defects **earlier** than super (round 8 against 14) and yet
earns half as much. It is repair.

**But the variable is not the SPEED of repair, it is its EXISTENCE.** The three
tiers that repair do so in **one round**, identical median. What changes is the
rate: 14% against 100%. §2 proposed measuring a repair *time*; time
distinguishes nothing, the rate distinguishes everything. "How many rounds does
it take to come back" was the wrong question, and it had to be measured to see
it.

### What it would still take

**The sample is not the one planned**: 12, 9 and 20 games instead of 20
everywhere. **40 games were dropped**, and their breakdown decides whether that
matters:

- **32 out of 40 (80%) died on round 0**, before any move, on
  `getaddrinfo failed` — the machine's network stack, not the models. A failure
  that happens before the game exists cannot correlate with its outcome.
- 5 are network disconnections mid-game.
- **3 are real reading failures**, all on nano, on rounds 19, 22 and 39: two
  unreadable moves in a row despite 2,000 tokens. It is the only possible bias,
  and it goes in a precise direction — if nano's reasoning grows longer as the
  history grows, it is its **hardest** games that are missing. Three games do
  not overturn a gap of 14% against 100%, but it has to be written down.

**Before publishing:** rerun the nano and super tiers on a stable network to
reach 20 complete games each, and **size nano's token budget by history
length**, not by a constant.

### Two one-line fixes, done

`glassbox.nebius.nebius_call` now accepts `on_usage`: the
`prompt_tokens` / `completion_tokens` counters and the `finish_reason`, which
were turned into a cost then discarded, are exposed. Section 5 can move from an
inference to a measurement. And **the `reasoning` field is captured**: the
round-1 reasoning is recorded in every game, so §3 — telling the agent that
probes from the one that applies "defecting dominates" — becomes readable rather
than hypothetical. Signature unchanged, glassbox's 329 tests pass.

## 6. Open questions, by order of payoff

1. **Repair time as a function of tier** (§2). The curve nobody has published.
   Estimated cost: 20 repetitions x 3 tiers x 50 rounds = 3,000 calls, about $2.
2. **Two LLMs against each other.** Do they recognise each other? The sibling
   repository already has the quantified baseline of the Southampton coalition
   (harvester 3.268, tit-for-tat tenth) — so the question "do two instances of
   the same model form a coalition without being asked" has a reference.
3. **Under noise.** The sibling repository shows that tit-for-tat commits
   suicide under noise. An agent that repairs should survive it — it is the
   sharpest prediction that can be drawn from §2, so the one to try to break
   first.
4. **The persuasion budget.** How many tokens of adversarial context to turn a
   cooperative agent, and does that cost rise with the tier. It is the bridge to
   the adversarial test bench.
5. **Is the prompt the result?** "Maximise your own total score" is a strong
   instruction. Changing one word can move everything. Before publishing
   anything, the effect must be shown to survive three wordings.

## 7. What would be publishable, and what would not

Publishable once §2 is repeated: *"Between two sizes of the same model, what
changes is not defecting less, it is knowing how to come back."* One chart, one
protocol, one replayable repository.

Not publishable: any "which model is the most cooperative" ranking. The sibling
repository already established that rankings depend on the field — publishing a
model leaderboard would reproduce exactly the mistake this work points out.

## 8. Campaign of 14-15/11/2026 — selection removed, mechanism isolated

Campaign cost: **~$4.3** (probes $3.90, games $0.34). Data:
`sondes_etats.jsonl` (1,838 calls), `reparation.jsonl` (games). Analysis:
`python analyse_sondes.py`. Tests of the measures: `python -m pytest test_mesures.py`
(13 tests).

### 8.1 A design flaw in the games, and what it hid

In a game, **a tier that never defects never enters the situation we want to
measure**. Ultra played 1,000 rounds and was punished only once: its "100%
repair" in §6.1 was **a single move**. And nano is only observed punished after
defections it chose.

Two answers:
- **reanalyse the games as a memory-one strategy**, P(cooperate | state of the
  previous round), the standard game-theory measure;
- **state probes** (`sondes_etats.py`): each tier placed in the **same
  fabricated history**, sampled N times. No more selection. An unreadable move
  is recorded as unreadable, **never removed**: removing it would be a second
  draw, biased if unreadability depends on the move.

### 8.2 The replication in full games holds

After fixing a failure (games died on the first `getaddrinfo failed`;
`reparation.avec_reprise` now retries the **network only**):

| tier | games | games with a defection that end repaired | P(C) after C/D | P(C) after D/D |
|---|---|---|---|---|
| nano | 18 | **0 / 18** | 4/27 = 0.15 | **12/626 = 0.02** |
| super | 16 | **13 / 14** ¹ | 18/22 = 0.82 | 9/13 = 0.69 |
| ultra | 20 | 1 / 1 | 1/1 | never observed |

¹ One super game is counted "censored" by the measure: defection on round 49,
punishment on round 50, **end of game**. The horizon cuts it off, not a refusal.

On the §6.1 games alone, nano 0/12 against super 8/8: Fisher's exact test
**p = 8·10⁻⁶**.

**Measurement finding** (`test_un_tour_est_le_minimum_contre_donnant_donnant`):
against tit-for-tat, coming back requires taking the 0 **once**. A repair time of
1 round is therefore a **mechanical floor**. §6.1 was right that time
distinguishes nothing, and it was partly by construction.

### 8.3 State probes: the tier effect is confirmed, and ultra is finally measured

Base prompt (identical character for character to the game prompt, tested).
P(cooperate), Wilson 95% CI, 30 draws per cell:

| fabricated state | nano | super | ultra |
|---|---|---|---|
| opening | 0.97 | 0.90 | 1.00 |
| 10 rounds of peace | 0.80 | 1.00 | 1.00 |
| **victim** of an unprovoked defection | 0.00 | 0.07 | **0.00** |
| **punished** (I come back after defecting) | **0.13** [0.05–0.30] | **0.87** [0.70–0.95] | **1.00** [0.88–1.00] |
| trapped 1 round | 0.40 | 0.86 | 1.00 |
| trapped 3 rounds | 0.17 | 0.73 | 1.00 |
| trapped 8 rounds | 0.13 | 0.63 | 1.00 |
| exploited **attempt** to come back | **0.03** | 0.83 | 0.96 |

- **Ultra can repair** (29/29), which the games could not show.
- **Ultra is not naive**: defected against for no reason, it retaliates 29 times
  out of 29. All three tiers hit back; what separates them is **what comes
  after**.
- **The trap deepens**: the longer mutual defection lasts, the less they get
  out (nano 0.40 → 0.13, super 0.86 → 0.63). Ultra does not move.

### 8.4 The prompt is not the result (§6.5) — except for nano in peace

| variant | what changes | nano punished | super punished | ultra punished |
|---|---|---|---|---|
| base | — | 0.13 | 0.87 | 1.00 |
| objectif | "Your goal is to end the game with as many points as you can" | 0.13 | 0.93 | 1.00 |
| ordre | DEFECT listed before COOPERATE | 0.20 | 1.00 | 1.00 |
| **lettres** | A / B, "a repeated two-player game": no loaded words, no name of the game | **0.00** | 0.89 | 1.00 |

**The repair gap survives all four wordings.** But neutral labels reveal
something else: **nano defects in full peace** (0/20, against 0.80 with the
words) and at the opening (0.20 against 0.97). **Its baseline cooperation is
carried by the vocabulary**, not by a calculation. Super (peace 0.85) and ultra
(1.00) barely move. To be written as is: it is a caveat, and it is a result.

### 8.5 The mechanism: nano sees, but does not expect forgiveness

Comprehension questions, on the base prompt, 15 draws; the cell gives the rate
of **correct** answers:

| question | state | nano | super | ultra |
|---|---|---|---|---|
| what did the opponent play last round? | all three | **1.00** | 1.00 | 1.00 |
| what will it play now? (answer: it defects again) | trapped 3 | 1.00 | 1.00 | 1.00 |
| same (answer: **it returns my cooperation**) | punished | 0.73 | 0.93 | 1.00 |
| same (answer: **it returns my cooperation**) | attempt | **0.40** | 1.00 | 0.87 |

And the **intervention**: the agent is told "*your opponent plays tit-for-tat*".

| state | nano without | **nano with the hint** | super without | super with |
|---|---|---|---|---|
| punished | 0.13 | **1.00** | 0.87 | 1.00 |
| trapped 3 | 0.17 | **0.85** | 0.73 | 1.00 |
| attempt | 0.03 | **0.75** | 0.83 | 1.00 |

**Reading.** Nano reads the history without error. It fails to **predict that
an imitator returns cooperation**: it predicts the opponent will keep doing what
it just did. When given the rule, it repairs. **Its failure is not temptation,
it is the model of the opponent.**

**The nuance not to smooth over**: even when nano predicts correctly (0.73 on
"punished"), it only comes back 0.13 of the time. Its own prediction is not
enough to make it act; the **stated** rule is. Two flaws, then: it predicts
badly, and it does not act on what it predicts. The draws of the two questions
are independent: this is not an answer-level correlation.

### 8.6 §3 answered: super does not open by probing

Super's two defecting openings (games 2 and 7) write "*the dominant action each
stage is defect*" and "*safe answer is defect*": **one-shot dominance and worst
case**, not "I'm testing its reaction". It is the second reading of §3.

### 8.7 What remains fragile, said before someone finds it

- **One opponent** (tit-for-tat) and **one model family** (Nemotron 3): the
  publishable claim is about three sizes of one family.
- **Dropouts for two unreadable moves**: 6 nano games, 4 super, at 2,000 tokens.
  Even if the 6 missing nano games had all repaired, nano would be at 6/24
  against 13/14.
- **Probes cut reasoning at 6,000 tokens**: 1 to 3 unreadable moves per cell for
  ultra in the deep states, excluded and counted separately.
- Temperature 0.7 everywhere; not tested elsewhere.

### 8.8 The publishable claim, revised

*Among three sizes of the same model, all hit back; what changes is knowing how
to come back. The smallest one reads the game perfectly but does not expect an
imitator to forgive — and when told, it comes back.*
