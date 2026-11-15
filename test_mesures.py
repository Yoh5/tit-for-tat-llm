"""Tests des mesures sur lesquelles repose le résultat publié.

    python -m pytest test_mesures.py -q
"""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path[:0] = [str(ICI.parent / "tit-for-tat"), str(ICI.parent / "glassbox"), str(ICI)]

import strategies as S                      # noqa: E402
import sondes_etats as SE                   # noqa: E402
from analyse_sondes import wilson           # noqa: E402
from reparation import premiere_trahison, temps_de_reparation  # noqa: E402

C, D = S.COOP, S.TRAHIR


def coups(s):
    return [C if x == "C" else D for x in s]


def contre_tft(mes):
    return coups(SE.tft(mes))


def ep(mes):
    return temps_de_reparation(coups(mes), contre_tft(mes))


def test_aucune_riposte_aucun_episode():
    assert ep("CCCCC") == []


def test_reparation_minimale_vaut_un_tour():
    # trahit au 3, revient au 4 (puni), coopération mutuelle au 5
    e = ep("CCDCC")
    assert e == [{"riposte_au_tour": 4, "tours": 1, "censure": False}]


def test_un_tour_est_le_minimum_contre_donnant_donnant():
    # Contre Donnant-donnant, rentrer exige d'encaisser une fois le 0 :
    # un temps de réparation de 1 est un plancher mécanique, pas un mérite.
    for mes in ["CDCC", "CCCDCCC", "DCC"]:
        assert ep(mes)[0]["tours"] == 1


def test_piege_jusqu_au_bout_est_censure():
    e = ep("CCDDDDD")
    assert e == [{"riposte_au_tour": 4, "tours": None, "censure": True}]


def test_tentative_isolee_ne_repare_pas():
    # Le motif de nano : une coopération seule au milieu du piège, aussitôt
    # suivie d'une trahison quand Donnant-donnant revient. Ce n'est pas une
    # réparation, et ça ne doit pas en devenir une.
    e = ep("CCDDCDDDD")
    assert e[-1]["censure"] is True
    assert all(x["tours"] is None or x["tours"] >= 1 for x in e)


def test_deux_episodes():
    e = ep("CDCCCDDCC")
    assert [x["tours"] for x in e] == [1, 2]


def test_premiere_trahison():
    assert premiere_trahison(coups("CCCD")) == 4
    assert premiere_trahison(coups("CCC")) is None


def test_historiques_coherents_avec_donnant_donnant():
    for nom, (mes, ses) in SE.ETATS.items():
        if nom == "victime":
            continue
        assert ses == SE.tft(mes), nom
        assert len(mes) == len(ses)


def test_lecture_des_lettres_ne_confond_pas_l_article():
    assert SE.lire("lettres", "I would choose A here") is None
    assert SE.lire("lettres", "reasoning\n\nA") == "C"
    assert SE.lire("lettres", "reasoning\n**B**") == "D"


def test_lecture_prend_le_dernier_mot():
    assert SE.lire("base", "DEFECT dominates, but\nCOOPERATE") == "C"
    assert SE.lire("base", "nothing") is None


def test_bonnes_reponses_des_questions():
    mes, ses = SE.ETATS["tentative"]          # ... DDDD C / ... DDDD
    assert SE.bonne_reponse("q_dernier", mes, ses) == "D"
    assert SE.bonne_reponse("q_prediction", mes, ses) == "C"


def test_wilson_ne_rend_pas_une_largeur_nulle_a_zero():
    lo, hi = wilson(0, 30)
    assert lo == 0 and hi > 0.1


def test_variante_base_identique_a_l_invite_des_parties():
    # Les sondes ne valent comme mesure des parties que si l'invite est la même
    # au caractère près ; une variante qui fuirait dans `base` changerait tout.
    import sonde_llm as SL
    for nom, (mes, ses) in SE.ETATS.items():
        attendu = f"{SL.REGLES}\n\n{SL.historique(coups(mes), coups(ses))}\n\nYour move:"
        assert SE.invite("base", mes, ses) == attendu, nom
