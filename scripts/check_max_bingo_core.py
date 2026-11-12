"""Exact new-game math/validation regressions; no source or provider requests."""
import itertools
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain import Ticket, validate_ticket
from app.rules import get_rule
from app.probability import probabilities


def check():
    rule = get_rule("bingo18")
    ticket = Ticket(rule.game_id, rule.mode_id, rule.rule_version, {"play": "single", "main": [1]})
    validate_ticket(rule, ticket)  # RED: old core rejects every Bingo ticket.
    from app.gameplay import bingo_choices, bingo_outcomes, pair_probability, sample_selections, ticket_capacity
    choices = [s for play in ("single", "double", "triple", "any_triple", "sum", "size") for s in bingo_choices(play)]
    assert len(choices) == 38
    outcomes = list(itertools.product(range(1, 7), repeat=3))
    for selection in choices:
        ticket.selections = selection
        validate_ticket(rule, ticket)
        actual = probabilities(rule, ticket)
        assert sum(actual.values()) == 1
        counts = {}
        for result in outcomes:
            events = bingo_outcomes(selection, result)
            assert sum(events.values()) <= 1
            hit = next((name for name, hit in events.items() if hit), "Không trúng")
            counts[hit] = counts.get(hit, 0) + 1
        assert all(p == Fraction(counts.get(name, 0), 216) for name, p in actual.items())
    ticket.selections = {"play": "single", "main": [1]}
    assert list(probabilities(rule, ticket).values()) == [Fraction(75,216), Fraction(15,216), Fraction(1,216), Fraction(125,216)]
    for play, value, expected in (("double", 1, Fraction(16,216)), ("triple", 1, Fraction(1,216)),
                                  ("sum", 10, Fraction(27,216)), ("size", "small", Fraction(81,216)),
                                  ("size", "tie", Fraction(54,216)), ("size", "big", Fraction(81,216))):
        ticket.selections = {"play": play, "main": [value]}
        assert sum(p for name,p in probabilities(rule,ticket).items() if name != "Không trúng") == expected
    for bad in ({"main":[1,2,3]}, {"play":"size","main":["Small"]}, {"play":"sum","main":[True]},
                {"play":"single","main":[0]}, {"play":"any_triple","main":[1]},
                {"play":"single","main":[1],"extra":1}, {"play":"sum","main":[19]}):
        ticket.selections = bad
        try: validate_ticket(rule, ticket)
        except ValueError: pass
        else: raise AssertionError(bad)
    assert ticket_capacity(rule,"any_triple") == 1
    assert ticket_capacity(rule,"sum") == 16
    assert ticket_capacity(rule,"size") == 3
    sum_counts = (1,3,6,10,15,21,25,27,27,25,21,15,10,6,3,1)
    for total, ways in zip(range(3,19),sum_counts):
        ticket.selections={"play":"sum","main":[total]}
        assert probabilities(rule,ticket)["Trúng"]==Fraction(ways,216)
    ticket.selections={"play":"any_triple","main":[]}
    assert probabilities(rule,ticket)["Trúng"]==Fraction(6,216)
    for game in ("max3d","max3dpro","bingo18"):
        r = get_rule(game)
        assert r.math_ready
        validate_ticket(r, Ticket(game,r.mode_id,r.rule_version,sample_selections(r)))
    for population in (2,3,4):
        for drawn in (2,3,4):
            rows=list(itertools.product(range(population),repeat=drawn))
            for same in (False,True):
                expected=sum(row.count(0)>=2 if same else 0 in row and 1 in row for row in rows)
                assert pair_probability(population,drawn,same) == Fraction(expected,len(rows))
    for game,main in (("max3d",["007"]),("max3dpro",["007","123"]),("max3dpro",["007","007"])):
        r=get_rule(game); t=Ticket(game,r.mode_id,r.rule_version,{"main":main})
        odds=probabilities(r,t)
        assert all(isinstance(p,Fraction) and 0<=p<=1 for p in odds.values())
        assert odds["Trúng ít nhất một giải"] + odds["Không trúng"] == 1
        if game=="max3d":
            assert odds["Giải Đặc biệt"] == 1-Fraction(999,1000)**2
            assert odds["Không trúng"] == Fraction(999,1000)**20
        else:
            assert odds["Giải Đặc biệt"] == odds["Giải phụ Đặc biệt"] == Fraction(1,1_000_000)
            assert odds["Giải Nhất"] == pair_probability(1000,4,main[0]==main[1])
            assert odds["Không trúng"] == Fraction(999 if main[0]==main[1] else 998,1000)**20
        for bad in (None, 7, {"bad":"shape"}):
            t.selections={"main":bad}
            try: validate_ticket(r,t)
            except ValueError: pass
            else: raise AssertionError("Malformed Max ticket accepted")
    print("Max/Bingo core OK: 38 choices, 216 outcomes, exact reduced-domain enumeration, validation and overlaps")


if __name__ == "__main__":
    check()
